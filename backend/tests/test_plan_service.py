import unittest

from app.core.config import Settings
from app.services.planner.travel_planner import TravelPlanner


VALID_JSON = """
{
  "source": "Mumbai",
  "destination": "Goa",
  "preferences": {
    "budget": 2500,
    "travel_style": "comfort",
    "people": 2,
    "days": 3
  },
  "best_option": {
    "mode": "sleeper bus",
    "price": 700,
    "duration": "10h",
    "reason": "it balances cost and comfort for an overnight trip"
  },
  "alternatives": [
    {
      "mode": "train",
      "price": 1200,
      "duration": "8h 30m",
      "reason": "it saves some time but is less flexible for late departures"
    },
    {
      "mode": "bus",
      "price": 950,
      "duration": "9h 30m",
      "reason": "it is slightly faster with improved sleeper comfort"
    }
  ],
  "itinerary": [
    {
      "day": 1,
      "plan": "Arrive in Goa, check in, and enjoy a relaxed beach evening."
    },
    {
      "day": 2,
      "plan": "Visit North Goa beaches, cafes, and a sunset cruise."
    },
    {
      "day": 3,
      "plan": "Explore Old Goa in the morning and depart later in the day."
    }
  ],
  "insight": "The bus keeps costs down while preserving most of the trip budget for the stay and activities."
}
""".strip()

OVERRIDE_JSON = """
{
  "source": "Delhi",
  "destination": "Jaipur",
  "preferences": {
    "budget": 3000,
    "travel_style": "budget",
    "people": 1,
    "days": 2
  },
  "best_option": {
    "mode": "flight",
    "price": 50,
    "duration": "1h",
    "reason": "the model guessed a very cheap flight"
  },
  "alternatives": [
    {
      "mode": "train",
      "price": 600,
      "duration": "5h",
      "reason": "train is practical and affordable"
    },
    {
      "mode": "bus",
      "price": 780,
      "duration": "6h",
      "reason": "night bus is direct and avoids transfers"
    }
  ],
  "itinerary": [
    {"day": 1, "plan": "Travel and explore central Jaipur."},
    {"day": 2, "plan": "Visit Amber Fort and local markets."}
  ],
  "insight": "This is a quick getaway."
}
""".strip()

NORMALIZATION_JSON = """
{
  "source": "Bangalore",
  "destination": "Chennai",
  "preferences": {
    "budget": "1500",
    "travel_style": "luxury",
    "people": "2",
    "days": 12
  },
  "best_option": {
    "mode": "coach",
    "price": 99,
    "duration": "6 hours",
    "reason": "cheap choice"
  },
  "alternatives": [
    {
      "mode": "rail",
      "price": 800,
      "duration": "5h 15m",
      "reason": "steady option"
    },
    {
      "mode": "bus",
      "price": 1100,
      "duration": "6h 40m",
      "reason": "comfortable overnight bus service"
    }
  ],
  "itinerary": [
    {"day": 1, "plan": "Start the trip."}
  ],
  "insight": "Flexible plan."
}
""".strip()


class StubGeminiClient:
    def __init__(self, responses: list[str] | None = None, error: Exception | None = None):
        self.responses = responses or []
        self.error = error
        self.calls = 0

    async def generate_response(self, prompt: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.responses:
            return self.responses.pop(0)
        return VALID_JSON


class TravelPlannerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings(gemini_api_key="test-key", max_itinerary_days=5)

    async def test_returns_valid_structured_plan(self) -> None:
        planner = TravelPlanner(self.settings, gemini_client=StubGeminiClient([VALID_JSON]))

        response = await planner.generate_travel_plan(
            "Plan a comfortable 3-day trip from Mumbai to Goa for 2 people under 2500 INR."
        )

        self.assertEqual(response.data.source, "Mumbai")
        self.assertEqual(response.data.best_option.mode, "bus")
        self.assertIn("deterministic score", response.data.best_option.reason.lower())
        self.assertIn("best option", response.response.lower())

    async def test_retries_once_when_first_response_is_not_parseable(self) -> None:
        planner = TravelPlanner(
            self.settings,
            gemini_client=StubGeminiClient(["not json", VALID_JSON]),
        )

        response = await planner.generate_travel_plan(
            "Plan a comfortable 3-day trip from Mumbai to Goa for 2 people under 2500 INR."
        )

        self.assertEqual(response.data.destination, "Goa")
        self.assertEqual(response.data.preferences.days, 3)

    async def test_raises_after_second_failure(self) -> None:
        planner = TravelPlanner(
            self.settings,
            gemini_client=StubGeminiClient(["not json", "still not json"]),
        )

        with self.assertRaises(RuntimeError):
            await planner.generate_travel_plan("Help me plan a trip.")

    async def test_raises_when_client_raises(self) -> None:
        planner = TravelPlanner(
            self.settings,
            gemini_client=StubGeminiClient(error=RuntimeError("network down")),
        )

        with self.assertRaises(RuntimeError):
            await planner.generate_travel_plan("Plan a fast trip from Delhi to Jaipur.")

    async def test_deterministic_scoring_can_override_llm_best_option(self) -> None:
        planner = TravelPlanner(self.settings, gemini_client=StubGeminiClient([OVERRIDE_JSON]))

        response = await planner.generate_travel_plan("Find the smartest low-cost way from Delhi to Jaipur.")

        self.assertIn(response.data.best_option.mode, {"bus", "train"})
        self.assertGreaterEqual(response.data.best_option.price, 250)
        self.assertNotEqual(response.data.best_option.mode, "flight")

    async def test_normalization_caps_itinerary_days_and_cleans_modes(self) -> None:
        planner = TravelPlanner(self.settings, gemini_client=StubGeminiClient([NORMALIZATION_JSON]))

        response = await planner.generate_travel_plan("Plan Bangalore to Chennai with a flexible budget.")

        self.assertEqual(response.data.preferences.days, 5)
        self.assertLessEqual(len(response.data.itinerary), 5)
        modes = {response.data.best_option.mode, *(item.mode for item in response.data.alternatives)}
        self.assertTrue(modes.issubset({"bus", "train", "flight"}))
        self.assertTrue(all(item.day >= 1 for item in response.data.itinerary))


if __name__ == "__main__":
    unittest.main()
