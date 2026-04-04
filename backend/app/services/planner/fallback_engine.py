from collections.abc import Mapping, Sequence
from random import randint
from typing import Any

from app.models.response import TravelOption


def _get_request_value(request: object, key: str, default: Any = None) -> Any:
    if isinstance(request, Mapping):
        return request.get(key, default)
    return getattr(request, key, default)


def _is_valid_option(option: object) -> bool:
    if not isinstance(option, TravelOption):
        return False
    return option.price >= 0 and option.duration_minutes >= 0 and option.reliability >= 0


def _is_same_option(a: TravelOption, b: TravelOption) -> bool:
    return a.mode == b.mode and a.route == b.route and a.price == b.price


def generate_bus_option(request: object) -> TravelOption:
    source = str(_get_request_value(request, "source", "source")).strip()
    destination = str(_get_request_value(request, "destination", "destination")).strip()
    return TravelOption(
        mode="bus",
        route=f"{source} -> {destination}",
        price=float(randint(500, 800)),
        duration="N/A",
        duration_minutes=0,
        reliability=0.65,
        reason="Always available backup",
        availability="Likely",
        booking_url=f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{destination.lower()}",
    )


def generate_alternative_option(
    best_option: TravelOption,
    trains: Sequence[TravelOption] | None,
    flights: Sequence[TravelOption] | None,
    request: object,
) -> TravelOption:
    valid_trains = [opt for opt in (trains or []) if _is_valid_option(opt)]
    valid_flights = [opt for opt in (flights or []) if _is_valid_option(opt)]
    bus_option = generate_bus_option(request)

    if best_option.mode == "train":
        return bus_option

    if best_option.mode == "flight":
        if valid_trains:
            selected = min(valid_trains, key=lambda item: (item.price, item.duration_minutes))
            return selected.model_copy(update={"reason": "Backup train option if flight fails"})
        return bus_option

    # If best is bus, prefer train, then flight, then bus.
    if valid_trains:
        selected = min(valid_trains, key=lambda item: (item.price, item.duration_minutes))
        return selected.model_copy(update={"reason": "Alternative to bus if available"})
    if valid_flights:
        selected = min(valid_flights, key=lambda item: (item.price, item.duration_minutes))
        return selected.model_copy(update={"reason": "Alternative to bus if available"})
    return bus_option


def generate_fallback(
    best_option: TravelOption,
    trains: Sequence[TravelOption] | None,
    flights: Sequence[TravelOption] | None,
    request: object,
) -> TravelOption:
    fallback = generate_alternative_option(best_option, trains, flights, request)
    if _is_same_option(best_option, fallback):
        fallback = generate_alternative_option(best_option, trains, flights, request)
    return fallback
