from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

from digital_wallet_rqm.domain.models import AccountBalance, Bank, PaymentReceipt, QrPayment, QrScan, QrUsage
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState

# Tools de solo mostrar: el cliente las dibuja como un componente en el chat y no devuelve resultado.
# Las emite el backend con los datos de sus tools; el LLM nunca las elige.
SHOW_ACCOUNT_BALANCE = "show_account_balance"
SHOW_QR_PAYMENT = "show_qr_payment"
SHOW_PAYMENT_RECEIPT = "show_payment_receipt"
DISPLAY_TOOLS = frozenset({SHOW_ACCOUNT_BALANCE, SHOW_QR_PAYMENT, SHOW_PAYMENT_RECEIPT})

# Tool del cliente cuyo resultado no se confirma: lo procesa el backend (nodo qr_payment)
SCAN_QR = "scan_qr"

# Resultado que se guarda para cada tarjeta: deja el par tool call / resultado completo en el historial
DISPLAYED = "displayed"


def client_can_display(state: BankState, name: str) -> bool:
    """True si el cliente declaró en AG-UI que sabe dibujar ese componente (REST /chat no declara nada)"""
    return any(tool.get("name") == name for tool in state.get("tools", []))


def balance_card_args(account: AccountBalance) -> dict[str, str]:
    """Args de show_account_balance; el saldo va como texto para no perder decimales en el JSON"""
    return {
        "account_number": account.account_number,
        "account_type": account.account_type,
        "currency": account.currency,
        "available": str(account.available),
    }


def qr_card_args(scan: QrScan) -> dict[str, Any]:
    """Args de show_qr_payment: datos del cobro, si todavía se puede pagar y las cuentas para pagar"""
    qr = scan.qr
    return {
        "code": qr.code,
        "recipient_name": qr.recipient_name,
        "bank": qr.bank.value,
        "account_number": qr.account_number,
        "document_id": qr.document_id,
        "amount": str(qr.amount),
        "currency": qr.currency,
        "usage": qr.usage.value,
        "expires_on": qr.expires_on.isoformat(),
        "note": qr.note,
        "expired": scan.expired,
        "already_paid": scan.already_paid,
        "accounts": [balance_card_args(account) for account in scan.accounts],
    }


def balance_from_card_args(args: dict[str, Any]) -> AccountBalance | None:
    """Vuelve a armar el saldo desde una tarjeta guardada; None si sus datos no tienen la forma esperada"""
    try:
        return AccountBalance(
            account_number=str(args["account_number"]),
            account_type=str(args["account_type"]),
            currency=str(args["currency"]),
            available=Decimal(str(args["available"])),
        )
    except (KeyError, InvalidOperation):
        return None


def qr_scan_from_card_args(args: dict[str, Any]) -> QrScan | None:
    """Vuelve a armar el cobro desde una tarjeta guardada; None si sus datos no tienen la forma esperada"""
    try:
        accounts = [balance_from_card_args(account) for account in args["accounts"]]
        if any(account is None for account in accounts):
            return None
        qr = QrPayment(
            code=str(args["code"]),
            recipient_name=str(args["recipient_name"]),
            bank=Bank(args["bank"]),
            account_number=str(args["account_number"]),
            document_id=str(args["document_id"]),
            amount=Decimal(str(args["amount"])),
            currency=str(args["currency"]),
            usage=QrUsage(args["usage"]),
            expires_on=date.fromisoformat(str(args["expires_on"])),
            note=str(args["note"]),
        )
        return QrScan(
            qr=qr,
            accounts=[account for account in accounts if account is not None],
            expired=bool(args["expired"]),
            already_paid=bool(args["already_paid"]),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return None


def receipt_card_args(receipt: PaymentReceipt) -> dict[str, str]:
    """Args de show_payment_receipt: el comprobante del pago, con montos como texto"""
    return {
        "receipt_number": receipt.receipt_number,
        "qr_code": receipt.qr_code,
        "recipient_name": receipt.recipient_name,
        "bank": receipt.bank.value,
        "destination_account": receipt.destination_account,
        "from_account": receipt.from_account,
        "amount": str(receipt.amount),
        "currency": receipt.currency,
        "balance_after": str(receipt.balance_after),
        "paid_at": receipt.paid_at.isoformat(),
    }


def receipt_from_card_args(args: dict[str, Any]) -> PaymentReceipt | None:
    """Vuelve a armar el comprobante desde una tarjeta guardada; None si sus datos no tienen la forma esperada"""
    try:
        return PaymentReceipt(
            receipt_number=str(args["receipt_number"]),
            qr_code=str(args["qr_code"]),
            recipient_name=str(args["recipient_name"]),
            bank=Bank(args["bank"]),
            destination_account=str(args["destination_account"]),
            from_account=str(args["from_account"]),
            amount=Decimal(str(args["amount"])),
            currency=str(args["currency"]),
            balance_after=Decimal(str(args["balance_after"])),
            paid_at=datetime.fromisoformat(str(args["paid_at"])),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return None


def display_messages(call_id: str, name: str, args: dict[str, Any]) -> list[AnyMessage]:
    """La tarjeta como tool call + su resultado, para guardarla en el checkpoint con el id que vio el navegador"""
    call = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
    return [call, ToolMessage(content=DISPLAYED, tool_call_id=call_id, name=name)]
