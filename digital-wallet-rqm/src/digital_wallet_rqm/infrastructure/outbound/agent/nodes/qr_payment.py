from uuid import uuid4

from langchain_core.callbacks import dispatch_custom_event
from langgraph.config import get_config
from langgraph.runtime import Runtime

from digital_wallet_rqm.domain.errors import QrNotFoundError
from digital_wallet_rqm.domain.models import QrScan
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import (
    SCAN_QR,
    SHOW_QR_PAYMENT,
    client_can_display,
    display_messages,
    qr_card_args,
)
from digital_wallet_rqm.infrastructure.outbound.agent.messages import scanned_qr
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import MANUALLY_EMIT_TOOL_CALL
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState, QrPaymentUpdate, ToolResult

CANCELLED = "cancelled"


def _result(content: str, awaiting_payment: str | None = None) -> QrPaymentUpdate:
    return {
        "tool_results": [ToolResult(tool=SCAN_QR, content=content)],
        "route": "bank_tools",
        "awaiting_payment": awaiting_payment,
    }


def _availability(scan: QrScan) -> str:
    """Si todavía se puede pagar y qué tiene que hacer el cliente"""
    if scan.expired:
        return "El QR está vencido: no se puede pagar."
    if scan.already_paid:
        return "El QR es de pago único y ya fue pagado: no se puede volver a pagar."
    return "Para pagar, el cliente elige la cuenta en la tarjeta y toca el botón Pay."


def _details(scan: QrScan) -> str:
    """Datos del cobro en texto, para un cliente que no dibuja la tarjeta"""
    qr = scan.qr
    amount = "el cliente asigna el monto" if qr.payer_sets_amount else f"{qr.amount:,.2f} {qr.currency}"
    return (
        f"Cobro QR de {qr.recipient_name} ({qr.bank.value}, cuenta {qr.account_number}): {amount}. "
        f"Nota: {qr.note}. Vence el {qr.expires_on.isoformat()}. {_availability(scan)}"
    )


def node_qr_payment(state: BankState, runtime: Runtime[GraphContext]) -> QrPaymentUpdate:
    """Procesa el QR que escaneó el navegador: busca el cobro y muestra la tarjeta para pagarlo. Sin LLM."""
    # 1. Qué devolvió el escáner: el token del QR o "cancelled"
    code = scanned_qr(state["messages"])
    if code is None or code == CANCELLED:
        return _result("El cliente cerró el escáner sin escanear un QR.")
    payments = runtime.context.payments
    if payments is None or runtime.context.user is None:
        return _result("Error: pagos no disponibles.")

    # 2. El caso de uso busca el cobro y las cuentas del cliente; un token desconocido no revela nada
    try:
        scan = payments.scan(runtime.context.user, code)
    except QrNotFoundError:
        return _result("El QR escaneado no es un QR de cobro válido.")
    print(f"[qr_payment]: {scan.qr.recipient_name} expired={scan.expired} paid={scan.already_paid}")

    # 3. Sin tarjeta (el cliente no la declaró), el texto lleva los datos del cobro
    if not client_can_display(state, SHOW_QR_PAYMENT):
        return _result(_details(scan))

    # 4. Tarjeta del cobro: se manda al navegador y queda en el historial con el mismo id
    call_id = f"qr-{uuid4().hex}"
    args = qr_card_args(scan)
    event = {"id": call_id, "name": SHOW_QR_PAYMENT, "args": args}
    # get_config: la config del run actual (LangGraph no tipa nodos con runtime y config a la vez)
    dispatch_custom_event(MANUALLY_EMIT_TOOL_CALL, event, config=get_config())
    amount = "el cliente asigna el monto" if scan.qr.payer_sets_amount else "monto fijo"
    summary = (
        f"Se mostró al cliente una tarjeta con el cobro QR de {scan.qr.recipient_name} ({scan.qr.bank.value}, "
        f"{amount}). Los montos se ven en la tarjeta. {_availability(scan)}"
    )
    # 5. Si se puede pagar, el grafo queda esperando la confirmación (qr_confirm) después de responder
    payable = not scan.expired and not scan.already_paid
    update = _result(summary, awaiting_payment=scan.qr.code if payable else None)
    update["messages"] = display_messages(call_id, SHOW_QR_PAYMENT, args)
    return update
