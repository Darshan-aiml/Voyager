import re
from datetime import datetime


def slugify_city(city: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", city.strip().lower()).strip("-")


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_duration_minutes(value: str | None) -> int:
    if not value:
        return 0
    pattern = re.compile(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?")
    match = pattern.fullmatch(value)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return (hours * 60) + minutes


def humanize_minutes(minutes: int) -> str:
    if minutes <= 0:
        return "N/A"
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"
