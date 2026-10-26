from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import CurrentUser


class AuthService(ABC):
    """Puerto de entrada de la autenticación: lo que la API le puede pedir"""

    @abstractmethod
    def login(self, nickname: str) -> str:
        """Devuelve un token para el usuario; si no existe lanza InvalidCredentialsError"""

    @abstractmethod
    def current_user(self, token: str) -> CurrentUser:
        """Devuelve el usuario dueño del token; si no es válido lanza InvalidTokenError"""
