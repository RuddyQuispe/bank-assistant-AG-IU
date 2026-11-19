from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from digital_wallet_rqm.application.ports.usage_repository import UsageRepository
from digital_wallet_rqm.domain.models import DailyUsage, TokenUsage
from digital_wallet_rqm.infrastructure.outbound.persistence.database import session_factory
from digital_wallet_rqm.infrastructure.outbound.persistence.entities import TokenUsageRecord


class SqlUsageRepository(UsageRepository):
    """Adaptador ORM del puerto UsageRepository (tabla "token_usage_daily")"""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessions = session_factory(engine)
        # SQLite y Postgres tienen su propio INSERT ... ON CONFLICT
        self._insert = postgres_insert if engine.dialect.name == "postgresql" else sqlite_insert

    async def add(self, user_id: str, day: date, usage: TokenUsage) -> None:
        # Upsert en una sola sentencia: dos runs simultáneos del mismo usuario no se pisan la suma
        # (leer, sumar y guardar serían dos consultas y uno de los dos se perdería)
        record = TokenUsageRecord
        statement = self._insert(record).values(
            user_id=user_id, day=day, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, runs=1
        )
        statement = statement.on_conflict_do_update(
            index_elements=[record.user_id, record.day],
            set_={
                "input_tokens": record.input_tokens + statement.excluded.input_tokens,
                "output_tokens": record.output_tokens + statement.excluded.output_tokens,
                "runs": record.runs + 1,
            },
        )
        async with self._sessions.begin() as db:
            await db.execute(statement)

    async def list_for_user(self, user_id: str, start: date, end: date) -> list[DailyUsage]:
        query = (
            select(TokenUsageRecord)
            .where(TokenUsageRecord.user_id == user_id, TokenUsageRecord.day.between(start, end))
            .order_by(TokenUsageRecord.day.desc())
        )
        async with self._sessions() as db:
            records = (await db.scalars(query)).all()
        return [record.to_domain() for record in records]
