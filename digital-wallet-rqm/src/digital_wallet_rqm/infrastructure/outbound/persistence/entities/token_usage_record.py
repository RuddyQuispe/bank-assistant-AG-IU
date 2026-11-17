from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from digital_wallet_rqm.domain.models import DailyUsage
from digital_wallet_rqm.infrastructure.outbound.persistence.entities.base import Base


class TokenUsageRecord(Base):
    """Tabla "token_usage_daily": consumo de tokens de chat por usuario y por día (hora de Bolivia)"""

    __tablename__ = "token_usage_daily"

    # Clave compuesta: un día nuevo es una fila nueva, así cada día empieza desde cero
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    runs: Mapped[int] = mapped_column(Integer)

    def to_domain(self) -> DailyUsage:
        return DailyUsage(self.day, self.input_tokens, self.output_tokens, self.runs)
