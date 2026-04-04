from __future__ import annotations

from typing import Any

DEFAULT_MODE_RANGES: dict[str, dict[str, int | float]] = {
    "bus": {"price_min": 450, "price_max": 2200, "duration_min": 240, "duration_max": 900, "rating": 3.8},
    "train": {"price_min": 300, "price_max": 2800, "duration_min": 180, "duration_max": 960, "rating": 4.1},
    "flight": {"price_min": 1800, "price_max": 12000, "duration_min": 60, "duration_max": 300, "rating": 4.0},
}

ROUTE_RANGES: dict[tuple[str, str], dict[str, dict[str, int | float]]] = {
    ("mumbai", "goa"): {
        "bus": {"price_min": 700, "price_max": 2200, "duration_min": 540, "duration_max": 780, "rating": 3.9},
        "train": {"price_min": 450, "price_max": 2200, "duration_min": 480, "duration_max": 720, "rating": 4.2},
        "flight": {"price_min": 2800, "price_max": 9000, "duration_min": 75, "duration_max": 120, "rating": 4.1},
    },
    ("delhi", "jaipur"): {
        "bus": {"price_min": 350, "price_max": 1400, "duration_min": 300, "duration_max": 420, "rating": 3.7},
        "train": {"price_min": 250, "price_max": 1800, "duration_min": 240, "duration_max": 360, "rating": 4.0},
        "flight": {"price_min": 2200, "price_max": 7000, "duration_min": 60, "duration_max": 90, "rating": 4.0},
    },
    ("bangalore", "chennai"): {
        "bus": {"price_min": 400, "price_max": 1800, "duration_min": 300, "duration_max": 480, "rating": 3.8},
        "train": {"price_min": 250, "price_max": 1600, "duration_min": 270, "duration_max": 420, "rating": 4.1},
        "flight": {"price_min": 1900, "price_max": 6500, "duration_min": 60, "duration_max": 90, "rating": 4.0},
    },
    ("chennai", "bengaluru"): {
        "bus": {"price_min": 400, "price_max": 1800, "duration_min": 300, "duration_max": 480, "rating": 3.8},
        "train": {"price_min": 250, "price_max": 1600, "duration_min": 270, "duration_max": 420, "rating": 4.1},
        "flight": {"price_min": 1900, "price_max": 6500, "duration_min": 60, "duration_max": 90, "rating": 4.0},
    },
}


def _normalize_location(value: str) -> str:
    return value.strip().lower()


def get_transport_grounding(source: str, destination: str, mode: str) -> dict[str, Any]:
    route_key = (_normalize_location(source), _normalize_location(destination))
    reverse_key = (_normalize_location(destination), _normalize_location(source))
    route_data = ROUTE_RANGES.get(route_key) or ROUTE_RANGES.get(reverse_key) or {}
    grounded = dict(DEFAULT_MODE_RANGES.get(mode, DEFAULT_MODE_RANGES["bus"]))
    grounded.update(route_data.get(mode, {}))
    return grounded
