from __future__ import annotations

import re
from typing import Any

from app.utils.helpers import slugify_city

VALID_MODES = {"bus", "train", "flight"}
MODE_ALIASES = {
    "sleeper bus": "bus",
    "volvo bus": "bus",
    "coach": "bus",
    "rail": "train",
    "train": "train",
    "flight": "flight",
    "plane": "flight",
    "air": "flight",
    "airplane": "flight",
    "bus": "bus",
}


def canonicalize_mode(value: Any) -> str:
    text = str(value or "bus").strip().lower()
    return MODE_ALIASES.get(text, next((mode for alias, mode in MODE_ALIASES.items() if alias in text), "bus"))


def normalize_duration(value: Any) -> tuple[str, int]:
    text = str(value or "0h").strip().lower()
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*h", text)
    minutes_match = re.search(r"(\d+)\s*m", text)

    total_minutes = 0
    if hours_match:
        total_minutes += int(float(hours_match.group(1)) * 60)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
    if total_minutes == 0:
        numeric = re.search(r"(\d+)", text)
        if numeric:
            total_minutes = int(numeric.group(1)) * 60
        else:
            total_minutes = 60

    hours, minutes = divmod(total_minutes, 60)
    if minutes:
        normalized = f"{hours}h {minutes}m"
    else:
        normalized = f"{hours}h"
    return normalized, total_minutes


def _normalize_number(value: Any, default: float, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, minimum)


def _normalize_int(value: Any, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def normalize_option(option: dict[str, Any] | None) -> dict[str, Any]:
    item = option or {}
    if not item.get("mode") or item.get("price") is None or not item.get("duration") or not item.get("reason"):
        raise ValueError("Each transport option must include mode, price, duration, and reason.")
    duration_text, duration_minutes = normalize_duration(item.get("duration"))
    price = round(_normalize_number(item.get("price"), default=0.0), 2)
    if price <= 0:
        raise ValueError("Each transport option must include a positive price.")
    return {
        "mode": "bus",
        "price": price,
        "duration": duration_text,
        "duration_minutes": duration_minutes,
        "reason": str(item.get("reason") or "").strip(),
        "rating": _normalize_number(item.get("rating"), default=0.0),
    }


def normalize_plan_payload(payload: dict[str, Any], *, max_itinerary_days: int) -> dict[str, Any]:
    source = str(payload.get("source") or "").strip()
    destination = str(payload.get("destination") or "").strip()
    if not source or not destination:
        raise ValueError("Source and destination are required in planner output.")

    preferences = payload.get("preferences") or {}
    days = _normalize_int(preferences.get("days"), default=1, minimum=1, maximum=max_itinerary_days)
    budget = _normalize_number(preferences.get("budget"), default=0.0)
    travel_style = str(preferences.get("travel_style") or "budget").strip().lower()
    if travel_style not in {"budget", "comfort", "fast"}:
        travel_style = "budget"

    best_option = normalize_option(payload.get("best_option"))
    alternatives = [normalize_option(option) for option in (payload.get("alternatives") or [])]
    options = [best_option, *alternatives]

    seen: set[tuple[str, float, int]] = set()
    deduped_options: list[dict[str, Any]] = []
    for option in options:
        key = (option["mode"], option["price"], option["duration_minutes"])
        if key in seen:
            continue
        seen.add(key)
        deduped_options.append(option)

    itinerary_items = payload.get("itinerary") or []
    if not isinstance(itinerary_items, list) or not itinerary_items:
        raise ValueError("Itinerary must contain at least one day.")
    normalized_itinerary: list[dict[str, Any]] = []
    for index, item in enumerate(itinerary_items[:days], start=1):
        plan_text = str((item or {}).get("plan") or "").strip()
        if not plan_text:
            raise ValueError("Each itinerary day must include a non-empty plan.")
        normalized_itinerary.append(
            {
                "day": index,
                "plan": plan_text,
            }
        )

    if len(deduped_options) < 3:
        raise ValueError("Planner must return at least 3 unique transport options.")

    primary = deduped_options[0]
    alternatives_only = deduped_options[1:4]
    insight = str(payload.get("insight") or "").strip()
    if not insight:
        raise ValueError("Planner insight is required.")

    return {
        "source": source,
        "destination": destination,
        "preferences": {
            "budget": budget,
            "travel_style": travel_style,
            "people": _normalize_int(preferences.get("people"), default=1, minimum=1, maximum=12),
            "days": days,
        },
        "best_option": primary,
        "alternatives": alternatives_only,
        "itinerary": normalized_itinerary,
        "insight": insight,
        "booking_url": f"https://www.redbus.in/bus-tickets/{slugify_city(source)}-to-{slugify_city(destination)}",
    }
