from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from digital_wallet_rqm.infrastructure.clock import business_today
from digital_wallet_rqm.infrastructure.settings import settings


def test_business_timezone_is_bolivia() -> None:
    # 2026-11-16 03:00 UTC son las 23:00 del 15/11 en La Paz (UTC-4): todavía cuenta para el día 15
    late_night = datetime(2026, 11, 16, 3, 0, tzinfo=UTC).astimezone(ZoneInfo(settings.USAGE_TIMEZONE))

    assert late_night.date() == date(2026, 11, 15)


def test_business_today_matches_the_local_date_in_bolivia() -> None:
    assert business_today() == datetime.now(ZoneInfo("America/La_Paz")).date()
