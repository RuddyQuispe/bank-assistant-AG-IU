from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import AccountBalance


class AccountRepository(ABC):
    """Puerto de salida de las cuentas del cliente (síncrono: lo usan las tools dentro del grafo)"""

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[AccountBalance]:
        """Cuentas del usuario, la principal primero; vacío si no tiene"""

    @abstractmethod
    def save(self, user_id: str, account: AccountBalance) -> None:
        """Guarda el nuevo saldo de una cuenta existente del usuario"""
