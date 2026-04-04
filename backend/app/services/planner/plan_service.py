from __future__ import annotations

from datetime import date

from app.core.config import Settings
from app.models.response import PlanTripResponse, TravelOption
from app.models.travel_response import TravelRecommendation
from app.services.planner.travel_planner import TravelPlanner


class PlanService:
    def __init__(
        self,
        settings: Settings,
        train_service=None,
        flight_service=None,
        bus_service=None,
        planner: TravelPlanner | None = None,
    ) -> None:
        self.settings = settings
        self.planner = planner or TravelPlanner(settings)

    async def generate_travel_plan(self, query: str):
        return await self.planner.generate_travel_plan(query)

    async def plan_trip(
        self, source: str, destination: str, travel_date: date, budget: float
    ) -> PlanTripResponse:
        query = (
            f"Plan a trip from {source} to {destination} on {travel_date.isoformat()} with a budget of {budget} INR. "
            "Choose the best travel mode, include alternatives, and build an itinerary."
        )
        plan = await self.generate_travel_plan(query)
        best_option = self._to_legacy_option(plan.data.best_option, source, destination)
        fallback_seed = plan.data.alternatives[0] if plan.data.alternatives else plan.data.best_option
        fallback_option = self._to_legacy_option(fallback_seed, source, destination)
        return PlanTripResponse(best_option=best_option, fallback_option=fallback_option)

    def _to_legacy_option(
        self,
        recommendation: TravelRecommendation,
        source: str,
        destination: str,
    ) -> TravelOption:
        return TravelOption(
            mode=recommendation.mode,
            route=f"{source} -> {destination}",
            price=recommendation.price,
            duration=recommendation.duration,
            duration_minutes=0,
            reliability=0.0,
            reason=recommendation.reason,
            availability="AI-estimated",
            booking_url=None,
            external_id=None,
        )
