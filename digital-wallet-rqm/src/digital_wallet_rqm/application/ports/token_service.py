from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import CurrentUser


class TokenService(ABC):
    """Puerto de salida de los tokens: emitir y leer. La aplicación no sabe que son JWT"""

    @abstractmethod
    def issue(self, user: CurrentUser) -> str:
        """Emite un token firmado para el usuario"""

    @abstractmethod
    def read(self, token: str) -> CurrentUser:
        """Devuelve el usuario del token; si no es válido lanza InvalidTokenError"""
