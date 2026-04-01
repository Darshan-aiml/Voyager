from collections.abc import Sequence

from app.models.response import TravelOption


def select_best_option(
    options: Sequence[TravelOption],
    budget: float,
    weight_price: float,
    weight_duration: float,
    weight_reliability: float,
) -> TravelOption | None:
    eligible = [opt for opt in options if opt.price <= budget]
    if not eligible:
        return None

    max_price = max(opt.price for opt in eligible) or 1
    max_duration = max(opt.duration_minutes for opt in eligible) or 1

    best_score = -1.0
    best_option: TravelOption | None = None

    for opt in eligible:
        price_score = 1 - (opt.price / max_price)
        duration_score = 1 - (opt.duration_minutes / max_duration) if opt.duration_minutes else 0
        reliability_score = opt.reliability

        score = (
            (weight_price * price_score)
            + (weight_duration * duration_score)
            + (weight_reliability * reliability_score)
        )

        if score > best_score:
            best_score = score
            best_option = opt

    return best_option
