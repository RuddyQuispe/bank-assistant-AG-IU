from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import CurrentUser


class UserRepository(ABC):
    """Puerto de salida de usuarios: dónde se buscan (hoy un usuario demo, mañana una tabla)"""

    @abstractmethod
    def find_by_nickname(self, nickname: str) -> CurrentUser | None:
        """Devuelve el usuario, o None si no existe"""
