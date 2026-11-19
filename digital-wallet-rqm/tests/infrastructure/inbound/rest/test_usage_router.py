from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.application.auth_use_cases import AuthUseCases
from digital_wallet_rqm.domain.errors import InvalidUsageRangeError
from digital_wallet_rqm.domain.models import CurrentUser, DailyUsage, UsageReport
from digital_wallet_rqm.infrastructure.inbound.dependencies import (
    get_auth_use_cases,
    get_current_user,
    get_usage_use_cases,
)
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import DemoUserRepository
from digital_wallet_rqm.infrastructure.outbound.security.jwt_token_service import JwtTokenService
from digital_wallet_rqm.main import app

TODAY = date(2026, 11, 16)


class FakeUsageService:
    """Servicio falso: guarda lo que se pidió y responde dos días"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date | None, date | None]] = []

    async def daily(self, user: CurrentUser, start: date | None = None, end: date | None = None) -> UsageReport:
        self.calls.append((user.user_id, start, end))
        if start and end and start > end:
            raise InvalidUsageRangeError()
        days = [DailyUsage(TODAY, 812, 95, 1), DailyUsage(date(2026, 11, 15), 48210, 6120, 37)]
        return UsageReport(today=TODAY, days=days)


@pytest.fixture
def service() -> Iterator[FakeUsageService]:
    fake = FakeUsageService()
    app.dependency_overrides[get_usage_use_cases] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="1", nickname="ruddy")
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(service: FakeUsageService) -> TestClient:
    return TestClient(app)


def test_daily_usage_returns_today_and_the_days_of_the_token_user(
    client: TestClient, service: FakeUsageService
) -> None:
    response = client.get("/usage/daily")

    assert response.status_code == 200
    assert response.json() == {
        "today": "2026-11-16",
        "days": [
            {"day": "2026-11-16", "input_tokens": 812, "output_tokens": 95, "runs": 1},
            {"day": "2026-11-15", "input_tokens": 48210, "output_tokens": 6120, "runs": 37},
        ],
    }
    assert service.calls == [("1", None, None)]


def test_daily_usage_passes_the_range(client: TestClient, service: FakeUsageService) -> None:
    client.get("/usage/daily", params={"from": "2026-11-01", "to": "2026-11-15"})

    assert service.calls == [("1", date(2026, 11, 1), date(2026, 11, 15))]


def test_inverted_range_is_a_400(client: TestClient) -> None:
    response = client.get("/usage/daily", params={"from": "2026-11-16", "to": "2026-11-15"})

    assert response.status_code == 400


def test_invalid_date_is_a_422(client: TestClient) -> None:
    assert client.get("/usage/daily", params={"from": "ayer"}).status_code == 422


def test_daily_usage_requires_a_token(service: FakeUsageService) -> None:
    # Filtro de auth real, sin token: nadie ve el consumo de otro
    del app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_auth_use_cases] = lambda: AuthUseCases(
        JwtTokenService("test-secret"), DemoUserRepository()
    )

    assert TestClient(app).get("/usage/daily").status_code == 401
    assert service.calls == []
