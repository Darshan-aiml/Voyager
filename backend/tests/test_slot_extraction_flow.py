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


class EmptyExtractor:
    async def extract(self, text: str) -> ExtractTripResponse:
        return ExtractTripResponse(
            raw_text=text,
            source=None,
            destination=None,
            date=None,
            people=None,
            days=None,
            preference=None,
        )


class SlotExtractionFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(plan_router, prefix="/api")
        response = TravelPlanApiResponse(
            text_response="ok",
            response="ok",
            data=TravelPlanData.model_validate(
                {
                    "source": "Chennai",
                    "destination": "Coimbatore",
                    "preferences": {
                        "budget": 2000,
                        "travel_style": "comfort",
                        "people": 2,
                        "days": 2,
                    },
                    "best_option": {
                        "mode": "bus",
                        "price": 850,
                        "duration": "8h",
                        "reason": "best tradeoff",
                    },
                    "alternatives": [
                        {
                            "mode": "bus",
                            "price": 920,
                            "duration": "7h 45m",
                            "reason": "faster option",
                        },
                        {
                            "mode": "bus",
                            "price": 760,
                            "duration": "9h",
                            "reason": "cheaper option",
                        },
                    ],
                    "itinerary": [{"day": 1, "plan": "Travel and check in."}],
                    "insight": "Good overnight route.",
                    "booking_url": "https://www.redbus.in/bus-tickets/chennai-to-coimbatore",
                }
            ),
        )
        app.dependency_overrides[get_plan_service] = lambda: StubPlanService(response)
        app.dependency_overrides[get_trip_extractor] = lambda: EmptyExtractor()
        self.client = TestClient(app)

    def test_extracts_english_x_to_y_and_asks_next_slot(self) -> None:
        response = self.client.post("/api/plan-trip", json={"query": "Chennai to Coimbatore"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "incomplete")
        self.assertEqual(payload["missing_field"], "date")
        self.assertEqual(payload["slot_state"]["source"], "Chennai")
        self.assertEqual(payload["slot_state"]["destination"], "Coimbatore")

    def test_extracts_arrow_pattern(self) -> None:
        response = self.client.post("/api/plan-trip", json={"query": "Hosur → Coimbatore"})
        payload = response.json()
        self.assertEqual(payload["slot_state"]["source"], "Hosur")
        self.assertEqual(payload["slot_state"]["destination"], "Coimbatore")

    def test_extracts_tamil_translit_pattern(self) -> None:
        response = self.client.post(
            "/api/plan-trip",
            json={"query": "Chennai la irundhu Coimbatore poganum"},
        )
        payload = response.json()
        self.assertEqual(payload["slot_state"]["source"], "Chennai")
        self.assertEqual(payload["slot_state"]["destination"], "Coimbatore")


if __name__ == "__main__":
    unittest.main()
