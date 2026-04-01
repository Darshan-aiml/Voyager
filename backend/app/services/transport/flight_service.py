import logging
from collections.abc import Sequence

import httpx

from app.core.config import Settings
from app.models.response import TravelOption
from app.utils.helpers import humanize_minutes

logger = logging.getLogger(__name__)


class FlightService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_flights(
        self, source_city: str, destination_city: str, travel_date: str
    ) -> Sequence[TravelOption]:
        if not self.settings.aviationstack_api_key:
            logger.warning("AviationStack API key not configured")
            return []

        source_iata = await self._resolve_city_iata(source_city)
        destination_iata = await self._resolve_city_iata(destination_city)
        if not source_iata or not destination_iata:
            logger.warning(
                "AviationStack city-to-IATA resolution failed for %s -> %s",
                source_city,
                destination_city,
            )
            return []

        url = f"{self.settings.aviationstack_base_url}/flights"
        params = {
            "access_key": self.settings.aviationstack_api_key,
            "dep_iata": source_iata.upper(),
            "arr_iata": destination_iata.upper(),
            "flight_date": travel_date,
            "limit": 20,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.exception("AviationStack flight search failed: %s", exc)
            return []

        options: list[TravelOption] = []
        for offer in payload.get("data", [])[:10]:
            try:
                airline = offer.get("airline", {}).get("name") or "Unknown Airline"
                departure_info = offer.get("departure", {})
                arrival_info = offer.get("arrival", {})

                dep_time = departure_info.get("scheduled")
                arr_time = arrival_info.get("scheduled")
                dep_airport = departure_info.get("iata") or source_iata.upper()
                arr_airport = arrival_info.get("iata") or destination_iata.upper()

                # AviationStack does not provide fare in the flight status feed.
                amount = 0.0
                duration_minutes = 0
                if dep_time and arr_time:
                    from datetime import datetime

                    dep_dt = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
                    arr_dt = datetime.fromisoformat(arr_time.replace("Z", "+00:00"))
                    duration_minutes = max(int((arr_dt - dep_dt).total_seconds() // 60), 0)

                options.append(
                    TravelOption(
                        mode="flight",
                        route=f"{dep_airport} -> {arr_airport} ({airline})",
                        price=amount,
                        duration=humanize_minutes(duration_minutes),
                        duration_minutes=duration_minutes,
                        reliability=self.settings.reliability_flight,
                        availability="Live",
                        reason=f"Live schedule from AviationStack; fare unavailable in provider feed",
                        external_id=offer.get("flight", {}).get("iata"),
                    )
                )
            except (KeyError, ValueError, TypeError):
                logger.warning("Skipping malformed flight offer")

        return options

    async def _resolve_city_iata(self, city_name: str) -> str | None:
        url = f"{self.settings.aviationstack_base_url}/airports"
        params = {
            "access_key": self.settings.aviationstack_api_key,
            "search": city_name,
            "limit": 10,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.exception("AviationStack location lookup failed: %s", exc)
            return None

        data = payload.get("data", [])
        for item in data:
            iata = item.get("iata_code")
            city = (item.get("city") or "").lower()
            if iata and city_name.lower() in city:
                return iata
        for item in data:
            iata = item.get("iata_code")
            if iata:
                return iata
        return None
