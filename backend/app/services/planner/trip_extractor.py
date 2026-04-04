from __future__ import annotations

import re

from app.core.config import Settings
from app.models.trip_extraction import ExtractTripResponse
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.parser import LLMOutputParseError, parse_json_response

EXTRACTION_PROMPT = """
You extract structured trip details from Indian travel-planning conversations.

Return valid JSON only with this exact schema:
{
  "source": string | null,
  "destination": string | null,
  "date": string | null,
  "days": number | null,
  "people": number | null,
  "preference": "cheap" | "comfort" | "luxury" | null
}

Rules:
- Use null for missing values.
- Keep city names short and clean.
- Preserve date phrases like "tomorrow", "next friday", or "12 May 2026" if present.
- Map budget/cheap/lowest cost to "cheap".
- Map comfort/balanced/premium sleeper to "comfort" when clearly requested.
- Map luxury/luxurious/premium/high-end to "luxury".
- Do not invent values.
- Return a single JSON object only.
- Do not add markdown, prose, or explanations.
""".strip()


class TripExtractor:
    def __init__(self, settings: Settings, gemini_client: GeminiClient | None = None) -> None:
        self.settings = settings
        self.gemini_client = gemini_client or GeminiClient(settings)

    async def extract(self, text: str) -> ExtractTripResponse:
        structured = await self._extract_with_model(text)
        if structured is None:
            structured = self._extract_with_regex(text)
        return ExtractTripResponse(raw_text=text, **structured)

    async def _extract_with_model(self, text: str) -> dict | None:
        try:
            raw_response = await self.gemini_client.generate_response(f"{EXTRACTION_PROMPT}\n\nConversation:\n{text}")
            parsed = parse_json_response(raw_response)
            return self._normalize_payload(parsed)
        except (RuntimeError, LLMOutputParseError, ValueError, Exception):
            return None

    def _normalize_payload(self, payload: dict) -> dict:
        normalized = self._extract_with_regex("")

        source = payload.get("source")
        destination = payload.get("destination")
        date = payload.get("date")
        days = payload.get("days")
        people = payload.get("people")
        preference = payload.get("preference")

        normalized["source"] = source.strip() if isinstance(source, str) and source.strip() else None
        normalized["destination"] = destination.strip() if isinstance(destination, str) and destination.strip() else None
        normalized["date"] = date.strip() if isinstance(date, str) and date.strip() else None
        normalized["days"] = int(days) if isinstance(days, (int, float)) and int(days) > 0 else None
        normalized["people"] = int(people) if isinstance(people, (int, float)) and int(people) > 0 else None
        normalized["preference"] = preference if preference in {"cheap", "comfort", "luxury"} else None
        return normalized

    def _extract_with_regex(self, text: str) -> dict:
        lower = text.lower()
        source = None
        destination = None
        date = None
        days = None
        people = None
        preference = None

        route_match = re.search(
            r"(?:from|starting from)\s+([A-Za-z][A-Za-z.\s]+?)\s+(?:to|for)\s+([A-Za-z][A-Za-z.\s]+?)(?:\s+for|\s+on|\s+next|\s+tomorrow|\s+with|\s+under|$)",
            text,
            re.IGNORECASE,
        )
        if route_match:
            source = route_match.group(1).strip(" .,")
            destination = route_match.group(2).strip(" .,")
        else:
            destination_match = re.search(r"(?:to|going to|visit)\s+([A-Za-z][A-Za-z.\s]+?)(?:\s+for|\s+on|\s+next|\s+tomorrow|\s+with|$)", text, re.IGNORECASE)
            if destination_match:
                destination = destination_match.group(1).strip(" .,")

        date_match = re.search(
            r"\b(today|tomorrow|day after tomorrow|next\s+[A-Za-z]+|this\s+[A-Za-z]+|\d{1,2}\s+[A-Za-z]+\s+\d{2,4}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
            lower,
        )
        if date_match:
            date = date_match.group(1).strip()

        days_match = re.search(r"(\d+)\s+(?:day|days|night|nights)\b", lower)
        if days_match:
            days = int(days_match.group(1))

        people_match = re.search(r"(\d+)\s+(?:people|persons|travelers|travellers|tickets|adults)\b", lower)
        if people_match:
            people = int(people_match.group(1))
        elif "solo" in lower:
            people = 1
        elif "couple" in lower:
            people = 2
        elif "family" in lower:
            people = 4

        if any(token in lower for token in ["cheap", "budget", "lowest cost", "affordable"]):
            preference = "cheap"
        elif any(token in lower for token in ["luxury", "luxurious", "premium", "high-end"]):
            preference = "luxury"
        elif any(token in lower for token in ["comfort", "comfortable", "balanced", "sleeper"]):
            preference = "comfort"

        return {
            "source": source,
            "destination": destination,
            "date": date,
            "days": days,
            "people": people,
            "preference": preference,
        }
