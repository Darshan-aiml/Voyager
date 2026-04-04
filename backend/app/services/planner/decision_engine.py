from collections.abc import Mapping, Sequence
from typing import Any

from app.models.response import TravelOption
from app.services.planner.fallback_engine import generate_bus_option


def _get_request_value(request: object, key: str, default: Any = None) -> Any:
    if isinstance(request, Mapping):
        return request.get(key, default)
    return getattr(request, key, default)


def _is_valid_option(option: object) -> bool:
    if not isinstance(option, TravelOption):
        return False
    return option.price >= 0 and option.duration_minutes >= 0 and option.reliability >= 0


def select_best_option(
    trains: Sequence[TravelOption] | None,
    flights: Sequence[TravelOption] | None,
    request: object,
) -> TravelOption:
    train_candidates = [opt for opt in (trains or []) if _is_valid_option(opt)]
    flight_candidates = [opt for opt in (flights or []) if _is_valid_option(opt)]
    combined = [*train_candidates, *flight_candidates]

    if not combined:
        return generate_bus_option(request)

    budget = _get_request_value(request, "budget")
    if isinstance(budget, (int, float)) and budget > 0:
        under_budget = [opt for opt in combined if opt.price <= float(budget)]
        if under_budget:
            combined = under_budget

    # Primary rank: lowest price, then shorter duration, then higher reliability.
    best = sorted(
        combined,
        key=lambda item: (
            item.price,
            item.duration_minutes if item.duration_minutes > 0 else 10**9,
            -item.reliability,
        ),
    )[0]
    return best
