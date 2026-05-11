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


def day_index(shift, when: date) -> int | None:
    """0..total_days-1 or None if outside the shift range."""
    if not shift:
        return None
    delta = (when - shift.start_date).days
    return delta if 0 <= delta < shift.total_days else None


def day_label(shift, when: date) -> str | None:
    idx = day_index(shift, when)
    if idx is None:
        return None
    if idx == 0:
        return "День заезда"
    if idx == shift.total_days - 1:
        return "День выезда"
    return f"День {idx}"
