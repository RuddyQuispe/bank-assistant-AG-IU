"""Consulta del consumo diario con un repositorio en memoria: sin base de datos ni FastAPI"""

from datetime import date

import pytest

from digital_wallet_rqm.application.ports.usage_repository import UsageRepository
from digital_wallet_rqm.application.usage_use_cases import UsageUseCases
from digital_wallet_rqm.domain.errors import InvalidUsageRangeError
from digital_wallet_rqm.domain.models import CurrentUser, DailyUsage, TokenUsage

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
TODAY = date(2026, 11, 16)


class RecordingUsage(UsageRepository):
    """Devuelve una fila fija y guarda el rango que se pidió"""

    def __init__(self) -> None:
        self.queries: list[tuple[str, date, date]] = []

    async def add(self, user_id: str, day: date, usage: TokenUsage) -> None:
        raise NotImplementedError

    async def list_for_user(self, user_id: str, start: date, end: date) -> list[DailyUsage]:
        self.queries.append((user_id, start, end))
        return [DailyUsage(TODAY, 812, 95, 1)]


@pytest.fixture
def repository() -> RecordingUsage:
    return RecordingUsage()


@pytest.fixture
def usage(repository: RecordingUsage) -> UsageUseCases:
    return UsageUseCases(usage=repository, today=lambda: TODAY)


async def test_daily_defaults_to_the_last_seven_days_including_today(
    usage: UsageUseCases, repository: RecordingUsage
) -> None:
    report = await usage.daily(RUDDY)

    assert repository.queries == [("1", date(2026, 11, 10), TODAY)]
    assert report.today == TODAY
    assert report.days == [DailyUsage(TODAY, 812, 95, 1)]


async def test_daily_uses_the_requested_range_for_the_token_user(
    usage: UsageUseCases, repository: RecordingUsage
) -> None:
    await usage.daily(RUDDY, start=date(2026, 11, 1), end=date(2026, 11, 15))

    assert repository.queries == [("1", date(2026, 11, 1), date(2026, 11, 15))]


async def test_start_after_end_is_rejected(usage: UsageUseCases) -> None:
    with pytest.raises(InvalidUsageRangeError):
        await usage.daily(RUDDY, start=date(2026, 11, 16), end=date(2026, 11, 15))


async def test_range_longer_than_a_year_is_rejected(usage: UsageUseCases) -> None:
    with pytest.raises(InvalidUsageRangeError):
        await usage.daily(RUDDY, start=date(2025, 1, 1), end=TODAY)
