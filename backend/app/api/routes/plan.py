import logging
import re
from datetime import date as dt_date

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.travel_request import TravelPlanRequest, TravelSlotState
from app.models.travel_response import CompletePlanResponse, IncompletePlanResponse, TravelPlanData
from app.services.planner.plan_service import PlanService
from app.services.planner.trip_extractor import TripExtractor
from app.utils.helpers import slugify_city

logger = logging.getLogger(__name__)
router = APIRouter()


def get_plan_service(settings: Settings = Depends(get_settings)) -> PlanService:
    return PlanService(settings=settings)


def get_trip_extractor(settings: Settings = Depends(get_settings)) -> TripExtractor:
    return TripExtractor(settings=settings)


def _date_to_string(value: dt_date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt_date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _clean_city_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" .,!?:;-")
    # Remove common conversational prefixes/suffixes in mixed-language inputs.
    cleaned = re.sub(r"^(?:i|me|naa|nan|nanu)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(?:la|il)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(?:city|town)$", "", cleaned, flags=re.IGNORECASE)
    if not cleaned:
        return None
    if re.search(r"[A-Za-z]", cleaned):
        return " ".join(part.capitalize() for part in cleaned.split(" "))
    return cleaned


def extract_entities(query: str) -> dict:
    entities = {
        "source": None,
        "destination": None,
        "date": None,
    }
    text = re.sub(r"\s+", " ", (query or "")).strip()
    if not text:
        return entities

    # 1) Arrow pattern: X -> Y or X → Y
    arrow_match = re.search(r"(?P<source>[^,;:!?]+?)\s*(?:->|=>|→)\s*(?P<destination>[^,;:!?]+)", text)
    if arrow_match:
        entities["source"] = _clean_city_name(arrow_match.group("source"))
        entities["destination"] = _clean_city_name(arrow_match.group("destination"))

    # 2) English patterns: from X to Y, or X to Y
    if not entities["source"] or not entities["destination"]:
        from_to_match = re.search(
            r"\bfrom\s+(?P<source>[A-Za-z][A-Za-z .'-]*?)\s+to\s+(?P<destination>[A-Za-z][A-Za-z .'-]*?)(?=$|\s+(?:on|for|with|under|in)\b|[,.!?])",
            text,
            flags=re.IGNORECASE,
        )
        if from_to_match:
            entities["source"] = entities["source"] or _clean_city_name(from_to_match.group("source"))
            entities["destination"] = entities["destination"] or _clean_city_name(from_to_match.group("destination"))

    if not entities["source"] or not entities["destination"]:
        to_match = re.search(
            r"(?P<source>[A-Za-z][A-Za-z .'-]*?)\s+to\s+(?P<destination>[A-Za-z][A-Za-z .'-]*?)(?=$|\s+(?:on|for|with|under|in)\b|[,.!?])",
            text,
            flags=re.IGNORECASE,
        )
        if to_match:
            entities["source"] = entities["source"] or _clean_city_name(to_match.group("source"))
            entities["destination"] = entities["destination"] or _clean_city_name(to_match.group("destination"))

    # 3) Tamil transliteration heuristics: "irundhu" for source, "kku/poganum" for destination.
    if not entities["source"]:
        tamil_source_match = re.search(
            r"(?P<source>[A-Za-z][A-Za-z .'-]*?)\s+(?:la\s+)?irundhu\b",
            text,
            flags=re.IGNORECASE,
        )
        if tamil_source_match:
            entities["source"] = _clean_city_name(tamil_source_match.group("source"))

    if not entities["destination"]:
        tamil_route_destination_match = re.search(
            r"irundhu\s+(?P<destination>[A-Za-z][A-Za-z .'-]*?)\s+poganum\b",
            text,
            flags=re.IGNORECASE,
        )
        if tamil_route_destination_match:
            entities["destination"] = _clean_city_name(tamil_route_destination_match.group("destination"))

    if not entities["destination"]:
        tamil_destination_match = re.search(
            r"(?P<destination>[A-Za-z][A-Za-z .'-]*?)\s+kku\s+poganum\b",
            text,
            flags=re.IGNORECASE,
        )
        if tamil_destination_match:
            entities["destination"] = _clean_city_name(tamil_destination_match.group("destination"))

    if not entities["destination"]:
        tamil_destination_fallback = re.search(
            r"(?:to\s+)?(?P<destination>[A-Za-z][A-Za-z .'-]*?)\s+poganum\b",
            text,
            flags=re.IGNORECASE,
        )
        if tamil_destination_fallback:
            entities["destination"] = _clean_city_name(tamil_destination_fallback.group("destination"))

    date_match = re.search(
        r"\b(today|tomorrow|day after tomorrow|next\s+[A-Za-z]+|this\s+[A-Za-z]+|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}\s+[A-Za-z]+(?:\s+\d{2,4})?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if date_match:
        entities["date"] = date_match.group(1).strip()

    return entities


def _merge_slot_state(payload: TravelPlanRequest, extracted_fields: dict, query_entities: dict) -> TravelSlotState:
    incoming = payload.slot_state.model_dump() if payload.slot_state else {}
    merged = {
        "source": payload.source or query_entities.get("source") or incoming.get("source") or extracted_fields.get("source"),
        "destination": payload.destination or query_entities.get("destination") or incoming.get("destination") or extracted_fields.get("destination"),
        "date": _date_to_string(payload.date) or query_entities.get("date") or _date_to_string(incoming.get("date")) or extracted_fields.get("date"),
        "people": payload.people or incoming.get("people") or extracted_fields.get("people"),
        "days": payload.days or incoming.get("days") or extracted_fields.get("days"),
        "preference": payload.preference or incoming.get("preference") or extracted_fields.get("preference"),
    }
    return TravelSlotState.model_validate(merged)


@router.post("/plan-trip", response_model=CompletePlanResponse | IncompletePlanResponse)
@router.post("/plan_trip", response_model=CompletePlanResponse | IncompletePlanResponse)
async def plan_trip(
    payload: TravelPlanRequest,
    plan_service: PlanService = Depends(get_plan_service),
    trip_extractor: TripExtractor = Depends(get_trip_extractor),
) -> CompletePlanResponse | IncompletePlanResponse:
    query_entities = extract_entities(payload.query or "")
    extracted_fields = {
        "source": None,
        "destination": None,
        "date": None,
        "days": None,
        "people": None,
        "preference": None,
    }
    if payload.query:
        extracted = await trip_extractor.extract(payload.query)
        extracted_fields = {
            "source": extracted.source,
            "destination": extracted.destination,
            "date": extracted.date,
            "days": extracted.days,
            "people": extracted.people,
            "preference": extracted.preference,
        }

    logger.info("/plan-trip extracted_entities=%s", query_entities)
    slot_state = _merge_slot_state(payload, extracted_fields, query_entities)
    logger.info("/plan-trip merged_slot_state=%s", slot_state.model_dump())
    required_fields = ["source", "destination", "date", "people", "days", "preference"]
    missing_field = next((field for field in required_fields if not getattr(slot_state, field)), None)

    if missing_field:
        logger.info("/plan-trip incomplete request missing_field=%s", missing_field)
        return IncompletePlanResponse(
            status="incomplete",
            missing_field=missing_field,
            slot_state=slot_state.model_dump(),
        )

    query = payload.query or (
        f"Plan a {slot_state.preference} trip from {slot_state.source} to {slot_state.destination} "
        f"on {slot_state.date} for {slot_state.people} people for {slot_state.days} days."
    )
    logger.info("/plan-trip complete request source=%s destination=%s", slot_state.source, slot_state.destination)
    plan = await plan_service.generate_travel_plan(query)
    normalized_data = plan.data.model_dump()
    normalized_data["source"] = str(slot_state.source)
    normalized_data["destination"] = str(slot_state.destination)
    normalized_data["preferences"]["people"] = int(slot_state.people)
    normalized_data["preferences"]["days"] = int(slot_state.days)
    normalized_data["booking_url"] = (
        f"https://www.redbus.in/bus-tickets/"
        f"{slugify_city(str(slot_state.source))}-to-{slugify_city(str(slot_state.destination))}"
    )
    return CompletePlanResponse(status="complete", data=TravelPlanData.model_validate(normalized_data))
