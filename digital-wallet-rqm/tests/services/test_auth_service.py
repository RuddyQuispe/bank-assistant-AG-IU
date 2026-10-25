import jwt
import pytest

from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.auth_service import AuthService, InvalidTokenError

SECRET = "test-secret-with-at-least-32-bytes!!"
RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def test_token_returns_the_same_user():
    service = AuthService(SECRET)

    token = service.create_token(RUDDY)

    assert service.read_user(token) == RUDDY


def test_token_uses_standard_claims():
    token = AuthService(SECRET, issuer="digital-wallet-rqm").create_token(RUDDY)

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["sub"] == "1"
    assert claims["nickname"] == "ruddy"
    assert claims["iss"] == "digital-wallet-rqm"
    assert "exp" in claims


def test_expired_token_is_rejected():
    service = AuthService(SECRET, expire_minutes=-1)
    token = service.create_token(RUDDY)

    with pytest.raises(InvalidTokenError):
        service.read_user(token)


def test_token_signed_with_other_secret_is_rejected():
    token = AuthService("other-secret-with-at-least-32-bytes!").create_token(RUDDY)

    with pytest.raises(InvalidTokenError):
        AuthService(SECRET).read_user(token)


def test_token_from_other_issuer_is_rejected():
    token = AuthService(SECRET, issuer="otra-app").create_token(RUDDY)

    with pytest.raises(InvalidTokenError):
        AuthService(SECRET, issuer="digital-wallet-rqm").read_user(token)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        AuthService(SECRET).read_user("no-es-un-jwt")


def test_authenticate_only_knows_the_demo_user():
    service = AuthService(SECRET)

    assert service.authenticate("ruddy") == RUDDY
    assert service.authenticate("juan") is None


def test_empty_secret_fails_on_creation():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        AuthService("")
