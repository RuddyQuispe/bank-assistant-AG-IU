from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.application.auth_use_cases import AuthUseCases
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.inbound.dependencies import (
    get_auth_use_cases,
    get_current_user,
    get_demo_qr_repository,
)
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import (
    DEMO_QR_EXPIRED,
    DEMO_QR_FIXED,
    DEMO_QR_OPEN,
    DemoQrRepository,
    DemoUserRepository,
)
from digital_wallet_rqm.infrastructure.outbound.security.jwt_token_service import JwtTokenService
from digital_wallet_rqm.main import app


@pytest.fixture(autouse=True)
def demo_qrs() -> Iterator[None]:
    app.dependency_overrides[get_demo_qr_repository] = lambda: DemoQrRepository(today=lambda: date(2026, 11, 18))
    yield
    app.dependency_overrides.clear()


def test_lists_only_the_demo_qr_tokens() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="1", nickname="ruddy")

    response = TestClient(app).get("/qr/demo")

    assert response.status_code == 200
    # Solo los tokens: los datos del cobro los da el backend al escanear
    assert response.json() == {"codes": [DEMO_QR_FIXED, DEMO_QR_OPEN, DEMO_QR_EXPIRED]}


def test_requires_a_token() -> None:
    app.dependency_overrides[get_auth_use_cases] = lambda: AuthUseCases(
        JwtTokenService("test-secret"), DemoUserRepository()
    )

    assert TestClient(app).get("/qr/demo").status_code == 401
