from datetime import date
import unittest

from app.core.config import Settings
from app.models.response import TravelOption
from app.services.planner.plan_service import PlanService


def make_option(
    *,
    mode: str,
    route: str,
    price: float,
    duration_minutes: int,
    reliability: float,
    reason: str | None = None,
) -> TravelOption:
    return TravelOption(
        mode=mode,
        route=route,
        price=price,
        duration=f"{duration_minutes // 60}h" if duration_minutes else "N/A",
        duration_minutes=duration_minutes,
        reliability=reliability,
        reason=reason,
        availability="Available",
    )


class StubTrainService:
    def __init__(self, options=None, error: Exception | None = None):
        self.options = options if options is not None else []
        self.error = error

    async def fetch_trains(self, source: str, destination: str, travel_date: str):
        if self.error:
            raise self.error
        return self.options


class StubFlightService:
    def __init__(self, options=None, error: Exception | None = None):
        self.options = options if options is not None else []
        self.error = error

    async def fetch_flights(self, source: str, destination: str, travel_date: str):
        if self.error:
            raise self.error
        return self.options


class StubBusService:
    def __init__(self, option: TravelOption | object | None = None, error: Exception | None = None):
        self.option = option
        self.error = error

    async def generate_option(
        self,
        source: str,
        destination: str,
        inferred_price: float = 0.0,
        inferred_duration_minutes: int = 0,
    ):
        if self.error:
            raise self.error
        if self.option is not None:
            return self.option
        return make_option(
            mode="bus",
            route=f"{source} -> {destination}",
            price=inferred_price,
            duration_minutes=inferred_duration_minutes,
            reliability=0.65,
            reason="Always available backup",
        )


class PlanServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings()
        self.travel_date = date(2026, 4, 1)

    async def test_selects_best_under_budget_and_returns_fallback(self) -> None:
        train = make_option(
            mode="train",
            route="Mumbai -> Goa (Konkan Express)",
            price=1200,
            duration_minutes=480,
            reliability=0.95,
        )
        flight = make_option(
            mode="flight",
            route="BOM -> GOI (Air Demo)",
            price=2500,
            duration_minutes=75,
            reliability=0.80,
        )
        service = PlanService(
            settings=self.settings,
            train_service=StubTrainService([train]),
            flight_service=StubFlightService([flight]),
            bus_service=StubBusService(),
        )

        response = await service.plan_trip("Mumbai", "Goa", self.travel_date, budget=3000)

        self.assertEqual(response.best_option.mode, "train")
        self.assertIsNotNone(response.fallback_option)
        self.assertEqual(response.fallback_option.mode, "bus")

    async def test_returns_lowest_price_when_budget_excludes_everything(self) -> None:
        train = make_option(
            mode="train",
            route="Mumbai -> Goa (Fast Train)",
            price=1800,
            duration_minutes=420,
            reliability=0.95,
        )
        flight = make_option(
            mode="flight",
            route="BOM -> GOI (Budget Air)",
            price=2200,
            duration_minutes=90,
            reliability=0.80,
        )
        service = PlanService(
            settings=self.settings,
            train_service=StubTrainService([train]),
            flight_service=StubFlightService([flight]),
            bus_service=StubBusService(),
        )

        response = await service.plan_trip("Mumbai", "Goa", self.travel_date, budget=100)

        self.assertEqual(response.best_option.price, 1800.0)
        self.assertEqual(
            response.best_option.reason,
            "No option within budget; selected lowest available fare",
        )
        self.assertIsNotNone(response.fallback_option)

    async def test_validation_failure_switches_to_bus_fallback(self) -> None:
        risky_train = make_option(
            mode="train",
            route="Mumbai -> Pune (Tight Transfer)",
            price=900,
            duration_minutes=180,
            reliability=0.95,
            reason="2026-04-01T10:00:00+05:30 | 2026-04-01T11:00:00+05:30",
        )
        service = PlanService(
            settings=self.settings.model_copy(update={"min_transfer_buffer_hours": 2}),
            train_service=StubTrainService([risky_train]),
            flight_service=StubFlightService([]),
            bus_service=StubBusService(),
        )

        response = await service.plan_trip("Mumbai", "Pune", self.travel_date, budget=2000)

        self.assertEqual(response.best_option.mode, "bus")
        self.assertEqual(response.fallback_option.mode, "bus")

    async def test_provider_crashes_still_return_a_safe_option(self) -> None:
        service = PlanService(
            settings=self.settings,
            train_service=StubTrainService(error=RuntimeError("train API down")),
            flight_service=StubFlightService(error=RuntimeError("flight API down")),
            bus_service=StubBusService(),
        )

        response = await service.plan_trip("Delhi", "Jaipur", self.travel_date, budget=1500)

        self.assertEqual(response.best_option.mode, "bus")
        self.assertEqual(response.fallback_option.mode, "bus")
        self.assertIn("Delhi -> Jaipur", response.best_option.route)

    async def test_bus_generator_crash_uses_emergency_fallback(self) -> None:
        service = PlanService(
            settings=self.settings,
            train_service=StubTrainService(error=RuntimeError("train API down")),
            flight_service=StubFlightService(error=RuntimeError("flight API down")),
            bus_service=StubBusService(error=RuntimeError("bus generator down")),
        )

        response = await service.plan_trip("Chennai", "Bengaluru", self.travel_date, budget=1500)

        self.assertEqual(response.best_option.mode, "bus")
        self.assertEqual(response.fallback_option.mode, "bus")
        self.assertEqual(response.best_option.price, 0.0)
        self.assertEqual(
            response.best_option.reason,
            "Emergency fallback generated after provider failure",
        )

    async def test_malformed_provider_data_is_ignored_without_crashing(self) -> None:
        valid_train = make_option(
            mode="train",
            route="Hyderabad -> Vizag (Night Express)",
            price=1300,
            duration_minutes=540,
            reliability=0.95,
        )
        service = PlanService(
            settings=self.settings,
            train_service=StubTrainService([valid_train, {"bad": "row"}]),
            flight_service=StubFlightService(
                [
                    make_option(
                        mode="flight",
                        route="HYD -> VTZ (Broken Fare)",
                        price=-400,
                        duration_minutes=60,
                        reliability=0.80,
                    )
                ]
            ),
            bus_service=StubBusService(),
        )

        response = await service.plan_trip("Hyderabad", "Vizag", self.travel_date, budget=2000)

        self.assertEqual(response.best_option.mode, "train")
        self.assertEqual(response.best_option.route, valid_train.route)
        self.assertIsNotNone(response.fallback_option)


if __name__ == "__main__":
    unittest.main()
