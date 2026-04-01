from datetime import date
import unittest

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.models.request import (
    BookingWorkflowActionRequest,
    ContactDetails,
    PassengerDetails,
    StartAutomatedBookingRequest,
)
from app.services.booking.automation_service import BookingAutomationService
from app.services.booking.booking_service import BookingService


def make_payload(*, mode: str = "train", payment_authorized: bool = False):
    return StartAutomatedBookingRequest(
        mode=mode,
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
        payment_authorized=payment_authorized,
    )


class BookingAutomationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        BookingAutomationService._workflows.clear()
        self.service = BookingAutomationService(BookingService())

    async def test_start_workflow_creates_provider_specific_steps(self) -> None:
        response = await self.service.start_workflow(make_payload(mode="bus"))

        self.assertEqual(response.mode, "bus")
        self.assertEqual(response.provider, "RedBus")
        self.assertEqual(response.next_action, "search_and_select")
        self.assertEqual(response.steps[0].status, "pending")
        self.assertEqual(response.steps[3].status, "blocked")
        self.assertTrue(response.steps[2].human_action_required)
        self.assertEqual(response.browser_automation.runner_name, "redbus_playwright_stub")
        self.assertTrue(
            response.browser_automation.script_path.endswith("redbus_playwright_stub.py")
        )

    async def test_requires_user_confirmation_before_automation(self) -> None:
        payload = make_payload()
        payload.user_confirmed_itinerary = False

        with self.assertRaises(HTTPException) as context:
            await self.service.start_workflow(payload)

        self.assertEqual(context.exception.status_code, 400)

    async def test_payment_authorization_unblocks_completion(self) -> None:
        response = await self.service.start_workflow(make_payload(mode="flight"))

        workflow_id = response.workflow_id
        await self.service.apply_action(
            workflow_id, BookingWorkflowActionRequest(action="confirm_search_results")
        )
        await self.service.apply_action(
            workflow_id, BookingWorkflowActionRequest(action="provide_traveller_details")
        )
        await self.service.apply_action(
            workflow_id, BookingWorkflowActionRequest(action="submit_otp")
        )
        updated = await self.service.apply_action(
            workflow_id,
            BookingWorkflowActionRequest(action="authorize_payment", note="User approved payment."),
        )

        self.assertEqual(updated.next_action, "complete_booking")
        self.assertFalse(updated.human_action_required)
        self.assertEqual(updated.steps[3].status, "completed")
        self.assertEqual(updated.steps[4].status, "pending")
        self.assertEqual(
            updated.browser_automation.next_stub_instruction,
            "Open https://www.google.com/travel/flights?from=mumbai&to=goa&date=2026-04-01 with Playwright and prepare the complete_booking step.",
        )


class BookingAutomationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        BookingAutomationService._workflows.clear()
        self.client = TestClient(app)

    def test_automate_booking_endpoint_and_actions(self) -> None:
        start_response = self.client.post(
            "/api/v1/automate-booking",
            json={
                "mode": "train",
                "source": "Mumbai",
                "destination": "Goa",
                "date": "2026-04-01",
                "passengers": [
                    {
                        "first_name": "Darshan",
                        "last_name": "R",
                        "age": 24,
                        "gender": "male",
                    }
                ],
                "contact": {
                    "phone": "9876543210",
                    "email": "darshan@example.com",
                },
                "user_confirmed_itinerary": True,
                "payment_authorized": False,
            },
        )

        self.assertEqual(start_response.status_code, 200)
        workflow_id = start_response.json()["workflow_id"]

        get_response = self.client.get(f"/api/v1/booking-workflows/{workflow_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["provider"], "IRCTC")
        self.assertEqual(
            get_response.json()["browser_automation"]["runner_name"],
            "irctc_playwright_stub",
        )

        action_response = self.client.post(
            f"/api/v1/booking-workflows/{workflow_id}/actions",
            json={"action": "confirm_search_results", "note": "Option selected by agent."},
        )
        self.assertEqual(action_response.status_code, 200)
        self.assertEqual(action_response.json()["next_action"], "fill_traveller_details")
        self.assertEqual(
            action_response.json()["browser_automation"]["next_stub_instruction"],
            "Navigate to the chosen IRCTC itinerary and stub-fill passenger, berth, and contact details.",
        )


if __name__ == "__main__":
    unittest.main()
