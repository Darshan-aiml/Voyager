import logging
from collections.abc import Sequence

import httpx

from app.core.config import Settings
from app.models.response import TravelOption

logger = logging.getLogger(__name__)


class TrainService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_trains(self, source: str, destination: str, travel_date: str) -> Sequence[TravelOption]:
        if not self.settings.railradar_api_key:
            logger.warning("RailRadar key not configured")
            return []

        headers = {
            "X-RapidAPI-Key": self.settings.railradar_api_key,
            "X-RapidAPI-Host": self.settings.railradar_api_host,
        }
        params = {"from": source, "to": destination, "date": travel_date}
        url = f"{self.settings.railradar_base_url}{self.settings.railradar_search_path}"

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.exception("RailRadar API failed: %s", exc)
            return []

        rows = payload.get("data") or payload.get("trains") or []
        options: list[TravelOption] = []

        for row in rows:
            try:
                train_name = row.get("train_name") or row.get("name") or "Train"
                dep = row.get("departure") or row.get("departure_time") or "N/A"
                arr = row.get("arrival") or row.get("arrival_time") or "N/A"
                duration_minutes = int(row.get("duration_minutes") or row.get("duration") or 0)
                price = float(row.get("price") or row.get("fare") or 450)
                availability = row.get("availability") or "Unknown"

                options.append(
                    TravelOption(
                        mode="train",
                        route=f"{source} -> {destination} ({train_name})",
                        price=price,
                        duration=f"{duration_minutes // 60}h" if duration_minutes else "N/A",
                        duration_minutes=duration_minutes,
                        reliability=self.settings.reliability_train,
                        availability=availability,
                        external_id=str(row.get("id") or row.get("train_number") or ""),
                        reason=f"Departure {dep}, arrival {arr}",
                    )
                )
            except (TypeError, ValueError):
                logger.warning("Skipping malformed train row")

        return options
