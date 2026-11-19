from decimal import Decimal, InvalidOperation
from uuid import uuid4

from langchain_core.callbacks import dispatch_custom_event
from langgraph.config import get_config
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from digital_wallet_rqm.domain.errors import AppError
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import (
    SHOW_PAYMENT_RECEIPT,
    client_can_display,
    display_messages,
    receipt_card_args,
)
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import MANUALLY_EMIT_TOOL_CALL
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState, QrConfirmUpdate, ToolResult

PAY_QR = "pay_qr"
INVALID_DECISION = "No se pudo pagar: los datos del pago no son válidos."


def _result(content: str) -> QrConfirmUpdate:
    return {"tool_results": [ToolResult(tool=PAY_QR, content=content)], "route": "bank_tools", "awaiting_payment": None}


def _parse_pay(decision: dict[str, object]) -> tuple[str, Decimal | None] | None:
    """Cuenta y monto elegidos por el cliente; None si no tienen la forma esperada"""
    account_number = decision.get("account_number")
    amount = decision.get("amount")
    if not isinstance(account_number, str) or not account_number:
        return None
    if amount is None:
        return account_number, None
    try:
        return account_number, Decimal(str(amount))
    except InvalidOperation:
        return None


def node_qr_confirm(state: BankState, runtime: Runtime[GraphContext]) -> QrConfirmUpdate:
    """Pausa el grafo hasta que el cliente confirme o cancele el pago del QR; si confirma, paga. Sin LLM."""
    # 1. El QR lo fija el backend al escanear: el navegador solo elige cuenta y monto
    code = state.get("awaiting_payment")
    if not code:
        return _result("No hay un pago pendiente.")

    # 2. Pausa: la web muestra el diálogo y reanuda con {"action": "pay" | "cancel", ...}.
    #    Al reanudar, LangGraph vuelve a correr el nodo desde el inicio: nada antes de interrupt tiene efectos
    decision = interrupt({"type": "qr_payment", "code": code})
    if not isinstance(decision, dict) or decision.get("action") not in ("pay", "cancel"):
        return _result(INVALID_DECISION)
    if decision["action"] == "cancel":
        return _result("El cliente canceló el pago.")
    choice = _parse_pay(decision)
    payments, user = runtime.context.payments, runtime.context.user
    if choice is None:
        return _result(INVALID_DECISION)
    if payments is None or user is None:
        return _result("Error: pagos no disponibles.")

    # 3. El caso de uso valida todo (vencido, ya pagado, moneda, monto, saldo) y descuenta
    account_number, amount = choice
    try:
        receipt = payments.pay(user, code, account_number=account_number, amount=amount)
    except AppError as error:
        return _result(f"No se pudo pagar: {error.detail}")
    print(f"[qr_confirm]: pagado {receipt.receipt_number} {receipt.amount} {receipt.currency}")

    # 4. Comprobante: tarjeta en el chat (si el cliente la dibuja) y en el historial, con el mismo id
    summary = f"Pago realizado a {receipt.recipient_name}, comprobante {receipt.receipt_number}."
    if not client_can_display(state, SHOW_PAYMENT_RECEIPT):
        return _result(f"{summary} Monto {receipt.amount:,.2f} {receipt.currency}.")
    call_id = f"receipt-{uuid4().hex}"
    args = receipt_card_args(receipt)
    event = {"id": call_id, "name": SHOW_PAYMENT_RECEIPT, "args": args}
    # get_config: la config del run actual (LangGraph no tipa nodos con runtime y config a la vez)
    dispatch_custom_event(MANUALLY_EMIT_TOOL_CALL, event, config=get_config())
    update = _result(f"{summary} Se mostró el comprobante en pantalla con el monto.")
    update["messages"] = display_messages(call_id, SHOW_PAYMENT_RECEIPT, args)
    return update
