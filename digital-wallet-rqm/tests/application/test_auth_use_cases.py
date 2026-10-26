"""Reglas del login probadas con dobles en memoria: sin JWT ni FastAPI"""

import pytest

from digital_wallet_rqm.application.auth_use_cases import AuthUseCases
from digital_wallet_rqm.application.ports.outbound.token_service import TokenService
from digital_wallet_rqm.application.ports.outbound.user_repository import UserRepository
from digital_wallet_rqm.domain.errors import InvalidCredentialsError, InvalidTokenError
from digital_wallet_rqm.domain.models import CurrentUser

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


class FakeTokens(TokenService):
    """Token legible: "token:<user_id>:<nickname>" """

    def issue(self, user: CurrentUser) -> str:
        return f"token:{user.user_id}:{user.nickname}"

    def read(self, token: str) -> CurrentUser:
        prefix, user_id, nickname = (token.split(":") + ["", ""])[:3]
        if prefix != "token":
            raise InvalidTokenError("formato desconocido")
        return CurrentUser(user_id=user_id, nickname=nickname)


class FakeUsers(UserRepository):
    def find_by_nickname(self, nickname: str) -> CurrentUser | None:
        return RUDDY if nickname == "ruddy" else None


@pytest.fixture
def auth() -> AuthUseCases:
    return AuthUseCases(tokens=FakeTokens(), users=FakeUsers())


def test_login_issues_a_token_for_an_existing_user(auth: AuthUseCases) -> None:
    assert auth.login("ruddy") == "token:1:ruddy"


def test_login_of_unknown_user_is_rejected(auth: AuthUseCases) -> None:
    with pytest.raises(InvalidCredentialsError):
        auth.login("juan")


def test_current_user_reads_the_token(auth: AuthUseCases) -> None:
    assert auth.current_user(auth.login("ruddy")) == RUDDY


def test_current_user_with_invalid_token_is_rejected(auth: AuthUseCases) -> None:
    with pytest.raises(InvalidTokenError):
        auth.current_user("no-es-un-token")
