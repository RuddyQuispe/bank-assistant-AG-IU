import logging
from dataclasses import dataclass
from datetime import datetime

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from digital_wallet_rqm.domain.models.chat_session import build_title
from digital_wallet_rqm.infrastructure.persistence.database import session_factory
from digital_wallet_rqm.infrastructure.persistence.entities import SessionRecord

logger = logging.getLogger(__name__)

# Clave de metadata donde la versión anterior guardaba el dueño de cada checkpoint
LEGACY_OWNER_KEY = "user_id"


@dataclass
class _LegacyThread:
    owner: str
    title: str | None
    created_at: datetime
    updated_at: datetime


async def import_legacy_sessions(engine: AsyncEngine, checkpointer: BaseCheckpointSaver[str]) -> int:
    """Crea la fila de "sessions" para las sesiones guardadas antes de esta tabla; devuelve cuántas creó.

    Antes de la tabla, el dueño viajaba en la metadata de cada checkpoint. Se corre al arrancar:
    es idempotente y no toca las sesiones que ya tienen fila. Los threads sin dueño no se importan
    (tampoco eran accesibles antes).
    """
    sessions = session_factory(engine)
    async with sessions() as db:
        known = set((await db.scalars(select(SessionRecord.session_id))).all())

    threads: dict[str, _LegacyThread] = {}
    # alist devuelve los checkpoints del más nuevo al más viejo
    async for checkpoint in checkpointer.alist(None):
        thread_id = checkpoint.config["configurable"]["thread_id"]
        owner = checkpoint.metadata.get(LEGACY_OWNER_KEY)
        if thread_id in known or not isinstance(owner, str):
            continue
        moment = datetime.fromisoformat(checkpoint.checkpoint["ts"])
        thread = threads.get(thread_id)
        if thread is None:
            # El checkpoint más nuevo tiene el historial completo: de ahí sale la primera pregunta
            messages: list[BaseMessage] = checkpoint.checkpoint["channel_values"].get("messages", [])
            first_question = next((message.text for message in messages if message.type == "human"), None)
            title = build_title(first_question) if first_question else None
            threads[thread_id] = _LegacyThread(owner, title, created_at=moment, updated_at=moment)
        else:
            thread.created_at = min(thread.created_at, moment)

    if not threads:
        return 0
    try:
        async with sessions.begin() as db:
            db.add_all(
                SessionRecord(
                    session_id=thread_id,
                    user_id=thread.owner,
                    title=thread.title,
                    created_at=thread.created_at,
                    updated_at=thread.updated_at,
                )
                for thread_id, thread in threads.items()
            )
    except SQLAlchemyError:
        # Una falla aquí no debe impedir que la app arranque: las sesiones viejas quedan sin importar
        # y se reintenta en el próximo arranque
        logger.exception("No se pudieron importar %d sesiones legacy", len(threads))
        return 0
    return len(threads)
