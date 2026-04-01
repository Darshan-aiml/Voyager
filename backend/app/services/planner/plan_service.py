import logging
from datetime import date
from collections.abc import Sequence

from app.core.config import Settings
from app.models.response import PlanTripResponse, TravelOption
from app.services.planner.decision_engine import select_best_option
from app.services.planner.fallback_engine import generate_fallback
from app.services.planner.validator import validate_plan
from app.services.transport.bus_service import BusService
from app.services.transport.flight_service import FlightService
from app.services.transport.train_service import TrainService

logger = logging.getLogger(__name__)


class PlanService:
    def __init__(
        self,
        settings: Settings,
        train_service: TrainService,
        flight_service: FlightService,
        bus_service: BusService,
    ) -> None:
        self.settings = settings
        self.train_service = train_service
        self.flight_service = flight_service
        self.bus_service = bus_service

    async def plan_trip(
        self, source: str, destination: str, travel_date: date, budget: float
    ) -> PlanTripResponse:
        travel_date_str = travel_date.isoformat()
        logger.info("Planning trip %s -> %s on %s", source, destination, travel_date_str)

        train_options = await self._safe_fetch_options(
            self.train_service.fetch_trains,
            source,
            destination,
            travel_date_str,
            provider_name="train",
        )
        flight_options = await self._safe_fetch_options(
            self.flight_service.fetch_flights,
            source,
            destination,
            travel_date_str,
            provider_name="flight",
        )
        primary_options = [*train_options, *flight_options]

        inferred_price = (
            min(item.price for item in primary_options) * 1.2 if primary_options else 0.0
        )
        inferred_duration_minutes = (
            max(item.duration_minutes for item in primary_options) if primary_options else 0
        )
        bus_option = await self._safe_generate_bus_option(
            source=source,
            destination=destination,
            inferred_price=round(inferred_price, 2),
            inferred_duration_minutes=inferred_duration_minutes,
        )

        all_options = [*primary_options, bus_option]

        best = select_best_option(
            all_options,
            budget,
            self.settings.score_weight_price,
            self.settings.score_weight_duration,
            self.settings.score_weight_reliability,
        )

        if best is None:
            logger.info("No option under budget, picking lowest-priced available option")
            best = min(all_options, key=lambda item: item.price)
            best.reason = "No option within budget; selected lowest available fare"

        validation_failed = not validate_plan(best, self.settings.min_transfer_buffer_hours)
        if validation_failed:
            logger.warning("Best option failed validation; switching to fallback")
            best = bus_option

        fallback = bus_option if validation_failed else generate_fallback(all_options, bus_option)
        if fallback.route == best.route and fallback.mode == best.mode:
            fallback = bus_option

        return PlanTripResponse(best_option=best, fallback_option=fallback)

    async def _safe_fetch_options(
        self,
        fetcher,
        source: str,
        destination: str,
        travel_date: str,
        *,
        provider_name: str,
    ) -> list[TravelOption]:
        try:
            options = await fetcher(source, destination, travel_date)
        except Exception as exc:
            logger.warning(
                "%s provider crashed, continuing with fallback path: %s",
                provider_name,
                exc,
            )
            return []

        return self._normalize_options(options, provider_name=provider_name)

    def _normalize_options(
        self, options: Sequence[TravelOption] | None, *, provider_name: str
    ) -> list[TravelOption]:
        if not options:
            return []

        normalized: list[TravelOption] = []
        for option in options:
            if not isinstance(option, TravelOption):
                logger.warning("Skipping malformed %s option of type %s", provider_name, type(option))
                continue

            if option.price < 0 or option.duration_minutes < 0 or option.reliability < 0:
                logger.warning("Skipping invalid %s option with negative values", provider_name)
                continue

            normalized.append(option)

        return normalized

    async def _safe_generate_bus_option(
        self,
        *,
        source: str,
        destination: str,
        inferred_price: float,
        inferred_duration_minutes: int,
    ) -> TravelOption:
        try:
            bus_option = await self.bus_service.generate_option(
                source,
                destination,
                inferred_price=max(inferred_price, 0.0),
                inferred_duration_minutes=max(inferred_duration_minutes, 0),
            )
        except Exception as exc:
            logger.warning("Bus fallback generation failed, using emergency fallback: %s", exc)
            return self._build_emergency_fallback(source, destination)

        if not isinstance(bus_option, TravelOption):
            logger.warning("Bus service returned malformed fallback, using emergency fallback")
            return self._build_emergency_fallback(source, destination)

        if bus_option.price < 0:
            bus_option.price = 0.0
        if bus_option.duration_minutes < 0:
            bus_option.duration_minutes = 0
            bus_option.duration = "N/A"
        if bus_option.reliability < 0:
            bus_option.reliability = self.settings.reliability_bus
        if not bus_option.reason:
            bus_option.reason = "Always available backup"

        return bus_option

    def _build_emergency_fallback(self, source: str, destination: str) -> TravelOption:
        return TravelOption(
            mode="bus",
            route=f"{source} -> {destination}",
            price=0.0,
            duration="N/A",
            duration_minutes=0,
            reliability=self.settings.reliability_bus,
            availability="Unknown",
            reason="Emergency fallback generated after provider failure",
            booking_url=None,
        )
