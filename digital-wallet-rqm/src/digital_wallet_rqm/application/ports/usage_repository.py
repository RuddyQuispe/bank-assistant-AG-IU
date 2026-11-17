from abc import ABC, abstractmethod
from datetime import date

from digital_wallet_rqm.domain.models import DailyUsage, TokenUsage


class UsageRepository(ABC):
    """Puerto de salida del consumo de tokens: una fila por usuario y por día"""

    @abstractmethod
    async def add(self, user_id: str, day: date, usage: TokenUsage) -> None:
        """Suma un run al consumo del usuario en ese día (la fila se crea en cero con el primer run)"""

    @abstractmethod
    async def list_for_user(self, user_id: str, start: date, end: date) -> list[DailyUsage]:
        """Consumo del usuario por día entre start y end (inclusive), el día más reciente primero"""
