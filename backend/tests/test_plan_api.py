import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.plan import get_plan_service, get_trip_extractor, router as plan_router
from app.models.trip_extraction import ExtractTripResponse
from app.models.travel_response import TravelPlanApiResponse, TravelPlanData
from app.services.planner.plan_service import PlanService


class StubPlanService(PlanService):
    def __init__(self, response: TravelPlanApiResponse):
        self._response = response

    async def generate_travel_plan(self, query: str) -> TravelPlanApiResponse:
        return self._response


class StubTripExtractor:
    async def extract(self, text: str) -> ExtractTripResponse:
        return ExtractTripResponse(
            raw_text=text,
            source="Mumbai",
            destination="Goa",
            date="2026-04-01",
            people=2,
            days=3,
            preference="comfort",
        )


class PlanApiTests(unittest.TestCase):
    def setUp(self) -> None:
        response = TravelPlanApiResponse(
            text_response="The best option is a sleeper bus for Rs 700 because it balances cost and comfort. I also created a 3-day itinerary for your trip to Goa.",
            response="The best option is a sleeper bus for Rs 700 because it balances cost and comfort. I also created a 3-day itinerary for your trip to Goa.",
            data=TravelPlanData.model_validate(
                {
                    "source": "Mumbai",
                    "destination": "Goa",
                    "preferences": {
                        "budget": 2500,
                        "travel_style": "comfort",
                        "people": 2,
                        "days": 3,
                    },
                    "best_option": {
                        "mode": "sleeper bus",
                        "price": 700,
                        "duration": "10h",
                        "reason": "it balances cost and comfort for an overnight trip",
                    },
                    "alternatives": [
                        {
                            "mode": "train",
                            "price": 1200,
                            "duration": "8h 30m",
                            "reason": "it is faster but usually costs more than the bus option",
                        }
                    ],
                    "itinerary": [
                        {"day": 1, "plan": "Arrive in Goa and settle near the beach."},
                        {"day": 2, "plan": "Explore North Goa and local food spots."},
                        {"day": 3, "plan": "Visit Old Goa and depart in the evening."},
                    ],
                    "insight": "An overnight surface trip preserves sightseeing time while keeping the total trip cost moderate.",
                    "booking_url": "https://www.redbus.in/bus-tickets/mumbai-to-goa",
                }
            ),
        )
        app = FastAPI()
        app.include_router(plan_router, prefix="/api")
        app.include_router(plan_router, prefix="/api/v1")
        app.dependency_overrides[get_plan_service] = lambda: StubPlanService(response)
        app.dependency_overrides[get_trip_extractor] = lambda: StubTripExtractor()
        self.client = TestClient(app)

    def test_invalid_request_returns_422(self) -> None:
        response = self.client.post(
            "/api/v1/plan-trip",
            json={"query": ""},
        )

        self.assertEqual(response.status_code, 422)

    def test_endpoint_returns_structured_ai_plan(self) -> None:
        response = self.client.post(
            "/api/plan-trip",
            json={
                "source": "Mumbai",
                "destination": "Goa",
                "date": "2026-04-01",
                "people": 2,
                "days": 3,
                "preference": "comfort",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["data"]["best_option"]["mode"], "sleeper bus")
        self.assertEqual(payload["data"]["preferences"]["days"], 3)
        self.assertEqual(payload["data"]["booking_url"], "https://www.redbus.in/bus-tickets/mumbai-to-goa")

    def test_underscore_route_alias_returns_structured_ai_plan(self) -> None:
        response = self.client.post(
            "/api/plan_trip",
            json={
                "source": "Mumbai",
                "destination": "Goa",
                "date": "2026-04-01",
                "people": 2,
                "days": 3,
                "preference": "comfort",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["data"]["best_option"]["mode"], "sleeper bus")


if __name__ == "__main__":
    unittest.main()
