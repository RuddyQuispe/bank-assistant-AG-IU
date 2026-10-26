from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from digital_wallet_rqm.models.session import TITLE_MAX_LENGTH, ChatSession
from digital_wallet_rqm.persistence.entities.base import Base


class SessionRecord(Base):
    """Tabla "sessions", en la misma base que las tablas de LangGraph (thread_id = session_id).

    Sin foreign key a "checkpoints": esa tabla es interna de LangGraph y su esquema puede cambiar.
    """

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Consulta del sidebar: sesiones del usuario, más recientes primero
    __table_args__ = (Index("ix_sessions_user_updated", "user_id", "updated_at"),)

    def to_domain(self) -> ChatSession:
        """La entidad no sale del repositorio: se convierte al modelo de dominio"""
        return ChatSession(
            session_id=self.session_id,
            user_id=self.user_id,
            title=self.title,
            created_at=_as_utc(self.created_at),
            updated_at=_as_utc(self.updated_at),
        )


def _as_utc(value: datetime) -> datetime:
    # SQLite no guarda la zona horaria: lo leído vuelve sin tzinfo aunque se guardó en UTC
    return value if value.tzinfo else value.replace(tzinfo=UTC)
