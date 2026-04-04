from __future__ import annotations

from typing import Any


STYLE_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "budget": (0.65, 0.25, 0.10),
    "comfort": (0.25, 0.35, 0.40),
    "fast": (0.20, 0.65, 0.15),
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def _normalize_inverse(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 1.0
    normalized = (value - minimum) / (maximum - minimum)
    return _clamp(1.0 - normalized)


def _normalize_rating(value: float | None) -> float:
    if value is None:
        return 0.5
    if value <= 1.0:
        return _clamp(value)
    return _clamp(value / 5.0)


def _affordability_score(price: float, budget: float | None) -> float:
    if not budget or budget <= 0:
        return 0.5
    return _clamp(1.0 - (price / budget))


def calculate_score(option: dict[str, Any], *, travel_style: str = "budget", budget: float | None = None) -> float:
    price = float(option.get("price", 0.0) or 0.0)
    duration_minutes = float(option.get("duration_minutes", 0.0) or 0.0)
    rating = option.get("rating")
    price_min = float(option.get("price_min", 0.0) or 0.0)
    price_max = float(option.get("price_max", max(price, price_min + 1.0)) or max(price, price_min + 1.0))
    duration_min = float(option.get("duration_min", 0.0) or 0.0)
    duration_max = float(
        option.get("duration_max", max(duration_minutes, duration_min + 1.0))
        or max(duration_minutes, duration_min + 1.0)
    )

    price_score = _normalize_inverse(price, price_min, price_max)
    price_score = (price_score + _affordability_score(price, budget)) / 2
    duration_score = _normalize_inverse(duration_minutes, duration_min, duration_max)
    rating_score = _normalize_rating(float(rating)) if rating is not None else 0.5
    weight_price, weight_duration, weight_rating = STYLE_WEIGHTS.get(travel_style, STYLE_WEIGHTS["budget"])

    score = (price_score * weight_price) + (duration_score * weight_duration) + (rating_score * weight_rating)
    return round(_clamp(score), 4)
