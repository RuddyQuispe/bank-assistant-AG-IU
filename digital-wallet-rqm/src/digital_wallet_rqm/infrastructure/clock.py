from datetime import date, datetime
from zoneinfo import ZoneInfo

from digital_wallet_rqm.infrastructure.settings import settings


def business_today() -> date:
    """Fecha actual en la zona horaria del negocio (Bolivia): el consumo diario empieza a las 00:00 local"""
    return datetime.now(ZoneInfo(settings.USAGE_TIMEZONE)).date()
