from collections.abc import Callable
from datetime import date, timedelta

from digital_wallet_rqm.application.ports.usage_repository import UsageRepository
from digital_wallet_rqm.domain.errors import InvalidUsageRangeError
from digital_wallet_rqm.domain.models import CurrentUser, UsageReport

# Sin rango, se muestran los últimos 7 días contando hoy
DEFAULT_DAYS = 7
MAX_RANGE = timedelta(days=366)


class UsageUseCases:
    """Consulta del consumo de tokens: cada usuario solo ve el suyo"""

    def __init__(self, usage: UsageRepository, today: Callable[[], date]) -> None:
        self.usage = usage
        self.today = today

    async def daily(self, user: CurrentUser, start: date | None = None, end: date | None = None) -> UsageReport:
        """Consumo del usuario por día (más reciente primero); los días sin consumo no aparecen"""
        today = self.today()
        end = end or today
        start = start or end - timedelta(days=DEFAULT_DAYS - 1)
        if start > end or end - start > MAX_RANGE:
            raise InvalidUsageRangeError()
        days = await self.usage.list_for_user(user.user_id, start, end)
        return UsageReport(today=today, days=days)
