from datetime import date
import unittest

from fastapi.testclient import TestClient

from app.api.routes.advisor import get_advisor_service
from app.api.routes.booking import get_booking_automation_service
from app.core.config import Settings
from app.main import app
from app.models.request import (
    ContactDetails,
    PassengerDetails,
    StartAutomatedBookingRequest,
)
from app.services.advisor.advisor_service import AdvisorService
from app.services.booking.automation_service import BookingAutomationService
from app.services.booking.booking_service import BookingService
from app.services.planner.plan_service import PlanService

from test_plan_api import CrashFlightService, CrashTrainService, StaticBusService


class AdvisorApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        BookingAutomationService._workflows.clear()
        plan_service = PlanService(
            settings=Settings(),
            train_service=CrashTrainService(),
            flight_service=CrashFlightService(),
            bus_service=StaticBusService(),
        )
        booking_service = BookingAutomationService(BookingService())
        workflow = await booking_service.start_workflow(
            StartAutomatedBookingRequest(
                mode="bus",
                source="Mumbai",
                destination="Goa",
                date=date(2026, 4, 1),
                passengers=[
                    PassengerDetails(
                        first_name="Darshan",
                        last_name="R",
                        age=24,
                        gender="male",
                    )
                ],
                contact=ContactDetails(
                    phone="9876543210",
                    email="darshan@example.com",
                ),
                user_confirmed_itinerary=True,
                payment_authorized=False,
            )
        )
        self.workflow_id = workflow.workflow_id

        app.dependency_overrides[get_advisor_service] = lambda: AdvisorService(
            plan_service=plan_service,
            booking_automation_service=booking_service,
        )
        app.dependency_overrides[get_booking_automation_service] = lambda: booking_service
        self.client = TestClient(app)

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_advisor_plan_response_is_grounded(self) -> None:
        response = self.client.post(
            "/api/v1/travel-advisor/respond",
            json={
                "intent": "plan_trip",
                "user_message": "What is the best way for me to go from Mumbai to Goa?",
                "source": "Mumbai",
                "destination": "Goa",
                "date": "2026-04-01",
                "budget": 2000,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "plan_trip")
        self.assertIn("best current option", payload["answer_brief"].lower())
        self.assertIn("best_option", payload["structured_context"])
        self.assertIn("fallback_option", payload["structured_context"])

    async def test_advisor_booking_response_mentions_next_step(self) -> None:
        response = self.client.post(
            "/api/v1/travel-advisor/respond",
            json={
                "intent": "booking_status",
                "user_message": "What is happening with my booking?",
                "workflow_id": self.workflow_id,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "booking_status")
        self.assertIn("next step", payload["answer_brief"].lower())
        self.assertEqual(payload["recommended_tools"], ["get_booking_workflow", "execute_booking_workflow"])


if __name__ == "__main__":
    unittest.main()
