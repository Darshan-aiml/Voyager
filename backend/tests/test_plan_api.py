from datetime import date
import unittest

from fastapi.testclient import TestClient

from app.api.routes.plan import get_plan_service
from app.core.config import Settings
from app.main import app
from app.models.response import TravelOption
from app.services.planner.plan_service import PlanService


class CrashTrainService:
    async def fetch_trains(self, source: str, destination: str, travel_date: str):
        raise RuntimeError("train provider outage")


class CrashFlightService:
    async def fetch_flights(self, source: str, destination: str, travel_date: str):
        raise RuntimeError("flight provider outage")


class StaticBusService:
    async def generate_option(
        self,
        source: str,
        destination: str,
        inferred_price: float = 0.0,
        inferred_duration_minutes: int = 0,
    ) -> TravelOption:
        return TravelOption(
            mode="bus",
            route=f"{source} -> {destination}",
            price=999.0,
            duration="8h",
            duration_minutes=480,
            reliability=0.65,
            reason="Always available backup",
            availability="Likely",
        )


class PlanApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_plan_service] = lambda: PlanService(
            settings=Settings(),
            train_service=CrashTrainService(),
            flight_service=CrashFlightService(),
            bus_service=StaticBusService(),
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_invalid_request_returns_422(self) -> None:
        response = self.client.post(
            "/api/v1/plan-trip",
            json={
                "source": "",
                "destination": "Goa",
                "date": date(2026, 4, 1).isoformat(),
                "budget": -5,
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_endpoint_returns_bus_fallback_during_provider_outage(self) -> None:
        response = self.client.post(
            "/api/v1/plan-trip",
            json={
                "source": "Mumbai",
                "destination": "Goa",
                "date": date(2026, 4, 1).isoformat(),
                "budget": 1500,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["best_option"]["mode"], "bus")
        self.assertEqual(payload["fallback_option"]["mode"], "bus")


if __name__ == "__main__":
    unittest.main()
