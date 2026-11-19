from datetime import date, datetime

from pydantic import BaseModel, Field

from digital_wallet_rqm.domain.models import AccountBalance, ChatSession, PaymentReceipt, QrScan


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
    session_id: str | None = Field(
        default=None,
        description="Id de una sesión existente; si se omite, el servidor crea una nueva y devuelve su id",
    )


class ChatResponse(BaseModel):
    session_id: str = Field(examples=["3f6c1c2e-8a1b-4c9e-9f2a-1d2e3f4a5b6c"])
    response: str = Field(examples=["Respuesta del asistente con las fuentes citadas al final."])


class BalanceCardResponse(BaseModel):
    """Tarjeta del saldo que el agente mostró en el chat"""

    account_number: str = Field(examples=["1001234567"])
    account_type: str = Field(examples=["Caja de ahorro"])
    currency: str = Field(description="Código ISO 4217", examples=["BOB"])
    available: str = Field(description="Saldo disponible como texto, sin perder decimales", examples=["1500.50"])

    @classmethod
    def from_domain(cls, card: AccountBalance) -> "BalanceCardResponse":
        return cls(
            account_number=card.account_number,
            account_type=card.account_type,
            currency=card.currency,
            available=str(card.available),
        )


class QrPaymentCardResponse(BaseModel):
    """Cobro QR que el agente mostró en el chat, como estaba al escanearlo"""

    code: str = Field(description="Token del QR", examples=["qr_af9bd6ff81dc2525a2fba110bf390946"])
    recipient_name: str = Field(examples=["Juan Pérez"])
    bank: str = Field(examples=["Banco Unión"])
    account_number: str = Field(description="Cuenta destino (8 dígitos)", examples=["12345678"])
    document_id: str = Field(description="NIT o carnet (8 dígitos)", examples=["87654321"])
    amount: str = Field(description="Monto como texto; \"0\" si lo asigna el pagador", examples=["350.00"])
    currency: str = Field(description="Código ISO 4217", examples=["BOB"])
    usage: str = Field(description="single (pago único) o multiple", examples=["single"])
    expires_on: date = Field(examples=["2026-12-18"])
    note: str = Field(examples=["Alquiler noviembre"])
    expired: bool
    already_paid: bool
    accounts: list[BalanceCardResponse] = Field(description="Cuentas del cliente para pagar")

    @classmethod
    def from_domain(cls, scan: QrScan) -> "QrPaymentCardResponse":
        qr = scan.qr
        return cls(
            code=qr.code,
            recipient_name=qr.recipient_name,
            bank=qr.bank.value,
            account_number=qr.account_number,
            document_id=qr.document_id,
            amount=str(qr.amount),
            currency=qr.currency,
            usage=qr.usage.value,
            expires_on=qr.expires_on,
            note=qr.note,
            expired=scan.expired,
            already_paid=scan.already_paid,
            accounts=[BalanceCardResponse.from_domain(account) for account in scan.accounts],
        )


class ReceiptResponse(BaseModel):
    """Comprobante de un pago con QR"""

    receipt_number: str = Field(examples=["PAY-3F9A1C2B7D"])
    qr_code: str = Field(description="Token del QR pagado", examples=["qr_af9bd6ff81dc2525a2fba110bf390946"])
    recipient_name: str = Field(examples=["Juan Pérez"])
    bank: str = Field(examples=["Banco Unión"])
    destination_account: str = Field(examples=["12345678"])
    from_account: str = Field(description="Cuenta del cliente que pagó", examples=["1001234567"])
    amount: str = Field(description="Monto pagado como texto", examples=["350.00"])
    currency: str = Field(examples=["BOB"])
    balance_after: str = Field(description="Saldo de la cuenta después del pago", examples=["1150.50"])
    paid_at: datetime

    @classmethod
    def from_domain(cls, receipt: PaymentReceipt) -> "ReceiptResponse":
        return cls(
            receipt_number=receipt.receipt_number,
            qr_code=receipt.qr_code,
            recipient_name=receipt.recipient_name,
            bank=receipt.bank.value,
            destination_account=receipt.destination_account,
            from_account=receipt.from_account,
            amount=str(receipt.amount),
            currency=receipt.currency,
            balance_after=str(receipt.balance_after),
            paid_at=receipt.paid_at,
        )


class MessageResponse(BaseModel):
    role: str = Field(description="human o ai", examples=["human"])
    content: str = Field(examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
    card: BalanceCardResponse | None = Field(
        default=None, description="Tarjeta del saldo que mostró el agente; en ese caso content viene vacío"
    )
    qr_payment: QrPaymentCardResponse | None = Field(
        default=None, description="Cobro QR que mostró el agente; en ese caso content viene vacío"
    )
    receipt: ReceiptResponse | None = Field(
        default=None, description="Comprobante de un pago con QR; en ese caso content viene vacío"
    )


class SessionResponse(BaseModel):
    session_id: str = Field(examples=["3f6c1c2e-8a1b-4c9e-9f2a-1d2e3f4a5b6c"])
    title: str | None = Field(
        description="Primeros 150 caracteres de la primera pregunta; null si aún no hay preguntas"
    )
    created_at: datetime
    updated_at: datetime = Field(description="Última actividad; el listado se ordena por este campo")

    @classmethod
    def from_domain(cls, session: ChatSession) -> "SessionResponse":
        return cls(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
