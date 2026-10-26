from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from digital_wallet_rqm.application.ports.outbound.session_repository import SessionRepository
from digital_wallet_rqm.domain.models.chat_session import ChatSession, build_title
from digital_wallet_rqm.infrastructure.persistence.database import session_factory
from digital_wallet_rqm.infrastructure.persistence.entities import SessionRecord


def _now() -> datetime:
    return datetime.now(UTC)


class SqlSessionRepository(SessionRepository):
    """Adaptador ORM del puerto SessionRepository (tabla "sessions")"""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessions = session_factory(engine)

    async def create(self, user_id: str) -> ChatSession:
        now = _now()
        record = SessionRecord(session_id=str(uuid4()), user_id=user_id, title=None, created_at=now, updated_at=now)
        async with self._sessions.begin() as db:
            db.add(record)
        return record.to_domain()

    async def find(self, session_id: str) -> ChatSession | None:
        async with self._sessions() as db:
            record = await db.get(SessionRecord, session_id)
        return record.to_domain() if record else None

    async def list_for_user(self, user_id: str) -> list[ChatSession]:
        query = (
            select(SessionRecord)
            .where(SessionRecord.user_id == user_id)
            .order_by(SessionRecord.updated_at.desc())
        )
        async with self._sessions() as db:
            records = (await db.scalars(query)).all()
        return [record.to_domain() for record in records]

    async def record_question(self, session_id: str, question: str) -> None:
        # Por sentencia y no por entidad: el UPDATE condicional es atómico, así dos preguntas
        # simultáneas no se pisan el título (cargar, modificar y guardar serían dos consultas)
        async with self._sessions.begin() as db:
            await db.execute(
                update(SessionRecord)
                .where(SessionRecord.session_id == session_id, SessionRecord.title.is_(None))
                .values(title=build_title(question))
            )
            await db.execute(
                update(SessionRecord).where(SessionRecord.session_id == session_id).values(updated_at=_now())
            )

    async def delete(self, session_id: str) -> None:
        async with self._sessions.begin() as db:
            # Por sentencia: borra sin cargar la entidad primero
            await db.execute(delete(SessionRecord).where(SessionRecord.session_id == session_id))
