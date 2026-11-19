import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from digital_wallet_rqm.domain.models.account_balance import AccountBalance

_EIGHT_DIGITS = re.compile(r"\d{8}")
# Lo único que lleva un QR: un token opaco y aleatorio. Los datos del cobro los guarda el banco
_QR_TOKEN = re.compile(r"qr_[0-9a-f]{32}")


def is_qr_token(code: str) -> bool:
    """True si el código tiene la forma de un token de QR ("qr_" + 32 hex en minúscula)"""
    return _QR_TOKEN.fullmatch(code) is not None


class Bank(StrEnum):
    """Bancos destino que acepta un QR"""

    UNION = "Banco Unión"
    ECONOMICO = "Banco Económico"
    GANADERO = "Banco Ganadero"
    BISA = "Banco BISA"
    MERCANTIL = "Banco Mercantil Santa Cruz"


class QrUsage(StrEnum):
    """Validez del QR: se paga una sola vez o se puede pagar muchas veces"""

    SINGLE = "single"
    MULTIPLE = "multiple"


@dataclass(frozen=True)
class QrPayment:
    """Datos de cobro que trae un QR"""

    code: str
    recipient_name: str
    bank: Bank
    # Cuenta destino y NIT o carnet: 8 dígitos
    account_number: str
    document_id: str
    # 0: el pagador asigna el monto
    amount: Decimal
    currency: str
    usage: QrUsage
    # Último día en que se puede pagar
    expires_on: date
    note: str

    def __post_init__(self) -> None:
        if not _EIGHT_DIGITS.fullmatch(self.account_number):
            raise ValueError("La cuenta destino debe tener 8 dígitos")
        if not _EIGHT_DIGITS.fullmatch(self.document_id):
            raise ValueError("El NIT o carnet debe tener 8 dígitos")
        if self.amount < 0:
            raise ValueError("El monto del QR no puede ser negativo")

    def is_expired(self, today: date) -> bool:
        return self.expires_on < today

    @property
    def payer_sets_amount(self) -> bool:
        return self.amount == 0


@dataclass(frozen=True)
class QrScan:
    """Lo que ve el cliente al escanear: el QR, sus cuentas para pagar y si todavía se puede pagar"""

    qr: QrPayment
    accounts: list[AccountBalance]
    expired: bool
    already_paid: bool


@dataclass(frozen=True)
class PaymentReceipt:
    """Comprobante de un pago con QR"""

    receipt_number: str
    qr_code: str
    recipient_name: str
    bank: Bank
    destination_account: str
    from_account: str
    amount: Decimal
    currency: str
    balance_after: Decimal
    paid_at: datetime
