import jwt
import pytest

from digital_wallet_rqm.domain.errors import InvalidTokenError
from digital_wallet_rqm.domain.models.current_user import CurrentUser
from digital_wallet_rqm.infrastructure.security.jwt_token_service import JwtTokenService

SECRET = "test-secret-with-at-least-32-bytes!!"
RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def test_token_returns_the_same_user() -> None:
    service = JwtTokenService(SECRET)

    token = service.issue(RUDDY)

    assert service.read(token) == RUDDY


def test_token_uses_standard_claims() -> None:
    token = JwtTokenService(SECRET, issuer="digital-wallet-rqm").issue(RUDDY)

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["sub"] == "1"
    assert claims["nickname"] == "ruddy"
    assert claims["iss"] == "digital-wallet-rqm"
    assert "exp" in claims


def test_expired_token_is_rejected() -> None:
    service = JwtTokenService(SECRET, expire_minutes=-1)
    token = service.issue(RUDDY)

    with pytest.raises(InvalidTokenError):
        service.read(token)


def test_token_signed_with_other_secret_is_rejected() -> None:
    token = JwtTokenService("other-secret-with-at-least-32-bytes!").issue(RUDDY)

    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET).read(token)


def test_token_from_other_issuer_is_rejected() -> None:
    token = JwtTokenService(SECRET, issuer="otra-app").issue(RUDDY)

    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET, issuer="digital-wallet-rqm").read(token)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET).read("no-es-un-jwt")


def test_empty_secret_fails_on_creation() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        JwtTokenService("")
