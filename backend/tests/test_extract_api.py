import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.extract import get_trip_extractor, router as extract_router
from app.models.trip_extraction import ExtractTripResponse
class StubTripExtractor:
    async def extract(self, text: str) -> ExtractTripResponse:
        return ExtractTripResponse(
            raw_text=text,
            source="Bangalore",
            destination="Goa",
            date="next friday",
            people=2,
            days=3,
            preference="comfort",
        )


class ExtractTripApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(extract_router, prefix="/api")
        app.include_router(extract_router, prefix="/api/v1")
        app.dependency_overrides[get_trip_extractor] = lambda: StubTripExtractor()
        self.client = TestClient(app)

    def test_extract_trip_endpoint_returns_slot_data(self) -> None:
        response = self.client.post("/api/extract-trip", json={"text": "I want to go from Bangalore to Goa next Friday for 2 people for 3 days."})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "Bangalore")
        self.assertEqual(payload["destination"], "Goa")
        self.assertEqual(payload["people"], 2)
        self.assertEqual(payload["days"], 3)
        self.assertEqual(payload["preference"], "comfort")


if __name__ == "__main__":
    unittest.main()
