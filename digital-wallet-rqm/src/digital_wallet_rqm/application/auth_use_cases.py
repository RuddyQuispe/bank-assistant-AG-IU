from digital_wallet_rqm.application.ports.token_service import TokenService
from digital_wallet_rqm.application.ports.user_repository import UserRepository
from digital_wallet_rqm.domain.errors import InvalidCredentialsError
from digital_wallet_rqm.domain.models import CurrentUser


class AuthUseCases:
    """Reglas del login: solo un usuario existente recibe token.

    Solo depende de puertos: no conoce FastAPI ni JWT.
    """

    def __init__(self, tokens: TokenService, users: UserRepository) -> None:
        self.tokens = tokens
        self.users = users

    def login(self, nickname: str) -> str:
        """Devuelve un token para el usuario; si no existe lanza InvalidCredentialsError"""
        user = self.users.find_by_nickname(nickname)
        if user is None:
            raise InvalidCredentialsError()
        return self.tokens.issue(user)

    def current_user(self, token: str) -> CurrentUser:
        """Devuelve el usuario dueño del token; si no es válido lanza InvalidTokenError"""
        return self.tokens.read(token)
