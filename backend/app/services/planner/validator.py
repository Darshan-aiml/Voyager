from datetime import timedelta

from app.models.response import TravelOption
from app.utils.helpers import parse_iso_datetime


def validate_plan(option: TravelOption, minimum_buffer_hours: int) -> bool:
    if option.mode in {"train", "flight"}:
        reason = option.reason or ""
        # Basic sanity check when reason contains ISO datetimes.
        parts = reason.split("|")
        if len(parts) == 2:
            arrival = parse_iso_datetime(parts[0].strip())
            next_departure = parse_iso_datetime(parts[1].strip())
            if arrival and next_departure:
                return next_departure - arrival >= timedelta(hours=minimum_buffer_hours)
    return True
