from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AccountBalance:
    """Saldo disponible de una cuenta del cliente"""

    account_number: str
    account_type: str
    # Código ISO 4217 (BOB, USD)
    currency: str
    available: Decimal

    @property
    def masked_number(self) -> str:
        # Solo los últimos 4 dígitos: así se puede nombrar la cuenta sin exponer el número
        return f"****{self.account_number[-4:]}"
