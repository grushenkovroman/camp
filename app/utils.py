from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from .config import Config


def today_local() -> date:
    return datetime.now(ZoneInfo(Config.TZ)).date()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def shift_date(d: date, days: int) -> date:
    return d + timedelta(days=days)
