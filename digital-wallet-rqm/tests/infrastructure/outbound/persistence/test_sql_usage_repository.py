import asyncio
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest

from digital_wallet_rqm.domain.models import DailyUsage, TokenUsage
from digital_wallet_rqm.infrastructure.outbound.persistence.database import database_url, get_engine
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import SqlUsageRepository

pytestmark = pytest.mark.anyio

NOV_15 = date(2026, 11, 15)
NOV_16 = date(2026, 11, 16)


@pytest.fixture
async def repository(tmp_path: Path) -> AsyncIterator[SqlUsageRepository]:
    async with get_engine(database_url(backend="sqlite", sqlite_path=tmp_path / "memory.db")) as engine:
        yield SqlUsageRepository(engine)


async def test_runs_of_the_same_user_and_day_add_up(repository: SqlUsageRepository) -> None:
    await repository.add("1", NOV_16, TokenUsage(800, 90))
    await repository.add("1", NOV_16, TokenUsage(12, 5))

    assert await repository.list_for_user("1", NOV_16, NOV_16) == [DailyUsage(NOV_16, 812, 95, runs=2)]


async def test_a_new_day_starts_from_zero(repository: SqlUsageRepository) -> None:
    await repository.add("1", NOV_15, TokenUsage(48210, 6120))
    await repository.add("1", NOV_16, TokenUsage(812, 95))

    # El más reciente primero; el día anterior queda como historial
    assert await repository.list_for_user("1", NOV_15, NOV_16) == [
        DailyUsage(NOV_16, 812, 95, runs=1),
        DailyUsage(NOV_15, 48210, 6120, runs=1),
    ]


async def test_each_user_has_its_own_rows(repository: SqlUsageRepository) -> None:
    await repository.add("1", NOV_16, TokenUsage(812, 95))
    await repository.add("2", NOV_16, TokenUsage(2140, 310))

    assert await repository.list_for_user("1", NOV_16, NOV_16) == [DailyUsage(NOV_16, 812, 95, runs=1)]


async def test_list_only_returns_days_inside_the_range(repository: SqlUsageRepository) -> None:
    await repository.add("1", NOV_15, TokenUsage(1, 1))
    await repository.add("1", NOV_16, TokenUsage(2, 2))

    assert await repository.list_for_user("1", NOV_16, NOV_16) == [DailyUsage(NOV_16, 2, 2, runs=1)]


async def test_concurrent_runs_do_not_lose_tokens(repository: SqlUsageRepository) -> None:
    # Upsert atómico: leer, sumar y guardar por separado perdería runs simultáneos
    await asyncio.gather(*(repository.add("1", NOV_16, TokenUsage(10, 1)) for _ in range(20)))

    assert await repository.list_for_user("1", NOV_16, NOV_16) == [DailyUsage(NOV_16, 200, 20, runs=20)]
