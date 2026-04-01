from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.models.request import BookingWorkflowActionRequest, StartAutomatedBookingRequest
from app.models.response import BookingWorkflowResponse, BookingWorkflowStep
from app.services.booking.booking_service import BookingService


@dataclass
class WorkflowState:
    workflow_id: str
    mode: str
    provider: str
    booking_url: str
    status: str
    next_action: str
    human_action_required: bool
    steps: list[BookingWorkflowStep]
    notes: list[str]
    created_at: datetime


class BookingAutomationService:
    _workflows: dict[str, WorkflowState] = {}

    def __init__(self, booking_service: BookingService) -> None:
        self.booking_service = booking_service

    async def start_workflow(
        self, payload: StartAutomatedBookingRequest
    ) -> BookingWorkflowResponse:
        if not payload.user_confirmed_itinerary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Automation can only start after the user confirms the itinerary.",
            )

        booking_url = await self.booking_service.get_booking_url(
            mode=payload.mode,
            source=payload.source,
            destination=payload.destination,
            travel_date=payload.date,
            external_id=payload.external_id,
        )

        provider = self._provider_name(payload.mode)
        workflow_id = str(uuid4())
        steps = self._build_steps(payload.mode, payment_authorized=payload.payment_authorized)

        state = WorkflowState(
            workflow_id=workflow_id,
            mode=payload.mode,
            provider=provider,
            booking_url=booking_url,
            status="awaiting_agent_action",
            next_action=steps[0].id,
            human_action_required=steps[0].human_action_required,
            steps=steps,
            notes=self._build_notes(payload.mode, payload.payment_authorized),
            created_at=datetime.now(UTC),
        )
        self._workflows[workflow_id] = state
        return self._to_response(state)

    async def apply_action(
        self, workflow_id: str, payload: BookingWorkflowActionRequest
    ) -> BookingWorkflowResponse:
        state = self._workflows.get(workflow_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking workflow not found.",
            )

        if state.status in {"completed", "failed"}:
            return self._to_response(state)

        action_map = {
            "confirm_search_results": "search_and_select",
            "provide_traveller_details": "fill_traveller_details",
            "submit_otp": "verify_user",
            "authorize_payment": "payment",
            "complete": "complete_booking",
            "fail": None,
        }
        target_step_id = action_map[payload.action]

        if payload.action == "fail":
            state.status = "failed"
            state.next_action = "none"
            state.human_action_required = False
            state.notes.append(payload.note or "Workflow failed and requires manual takeover.")
            self._mark_first_incomplete_step(state.steps, "blocked")
            return self._to_response(state)

        current_step = next((step for step in state.steps if step.id == target_step_id), None)
        if current_step is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested action does not match this workflow.",
            )

        if current_step.status in {"completed", "failed"}:
            return self._to_response(state)

        if current_step.status in {"pending", "blocked"}:
            current_step.status = "completed"
            if current_step.id == "payment":
                complete_step = next(step for step in state.steps if step.id == "complete_booking")
                if complete_step.status == "blocked":
                    complete_step.status = "pending"

        next_step = next((step for step in state.steps if step.status == "pending"), None)
        if next_step is None:
            next_step = next((step for step in state.steps if step.status == "blocked"), None)
        if next_step is None:
            state.status = "completed"
            state.next_action = "none"
            state.human_action_required = False
            return self._to_response(state)

        state.status = "awaiting_agent_action"
        state.next_action = next_step.id
        state.human_action_required = next_step.human_action_required
        if payload.note:
            state.notes.append(payload.note)
        return self._to_response(state)

    async def get_workflow(self, workflow_id: str) -> BookingWorkflowResponse:
        state = self._workflows.get(workflow_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking workflow not found.",
            )
        return self._to_response(state)

    def _build_steps(self, mode: str, *, payment_authorized: bool) -> list[BookingWorkflowStep]:
        provider_label = self._provider_name(mode)
        verify_details = "Verify logged-in account, OTP, or provider challenge before payment."
        payment_details = "Advance to checkout and stop before final payment capture."

        mode_specific_details = {
            "train": "Search IRCTC route, quota, and coach preferences.",
            "flight": "Search airline or aggregator fares and select cabin/fare family.",
            "bus": "Search RedBus route, operator, boarding, and drop points.",
        }

        payment_status = "pending" if payment_authorized else "blocked"
        payment_human_required = not payment_authorized

        return [
            BookingWorkflowStep(
                id="search_and_select",
                title=f"Search and select itinerary on {provider_label}",
                status="pending",
                automation_level="browser",
                human_action_required=False,
                details=mode_specific_details[mode],
            ),
            BookingWorkflowStep(
                id="fill_traveller_details",
                title="Fill traveller and contact details",
                status="pending",
                automation_level="browser",
                human_action_required=False,
                details="Enter passenger names, age, gender, and contact information.",
            ),
            BookingWorkflowStep(
                id="verify_user",
                title="Handle OTP or account verification checkpoint",
                status="pending",
                automation_level="human-in-the-loop",
                human_action_required=True,
                details=verify_details,
            ),
            BookingWorkflowStep(
                id="payment",
                title="Move to payment handoff",
                status=payment_status,
                automation_level="human-in-the-loop",
                human_action_required=payment_human_required,
                details=payment_details,
            ),
            BookingWorkflowStep(
                id="complete_booking",
                title="Mark booking workflow complete after confirmation",
                status="pending" if payment_authorized else "blocked",
                automation_level="agent",
                human_action_required=payment_human_required,
                details="Complete only after the user confirms checkout/payment succeeded.",
            ),
        ]

    def _build_notes(self, mode: str, payment_authorized: bool) -> list[str]:
        notes = [
            f"{self._provider_name(mode)} automation skeleton initialized.",
            "Use browser automation for search and form-filling; keep OTP and payment under explicit user control.",
        ]
        if not payment_authorized:
            notes.append("Payment step is blocked until the user explicitly authorizes payment.")
        return notes

    def _provider_name(self, mode: str) -> str:
        return {
            "train": "IRCTC",
            "flight": "Google Flights / airline checkout",
            "bus": "RedBus",
        }[mode]

    def _mark_first_incomplete_step(self, steps: list[BookingWorkflowStep], status_value: str) -> None:
        for step in steps:
            if step.status in {"pending", "blocked"}:
                step.status = status_value
                break

    def _to_response(self, state: WorkflowState) -> BookingWorkflowResponse:
        if state.next_action == "payment":
            payment_step = next(step for step in state.steps if step.id == "payment")
            complete_step = next(step for step in state.steps if step.id == "complete_booking")
            if payment_step.status == "completed" and complete_step.status == "blocked":
                complete_step.status = "pending"

        if state.next_action == "complete_booking":
            complete_step = next(step for step in state.steps if step.id == "complete_booking")
            complete_step.human_action_required = False
            state.human_action_required = False

        return BookingWorkflowResponse(
            workflow_id=state.workflow_id,
            mode=state.mode,
            provider=state.provider,
            booking_url=state.booking_url,
            status=state.status,
            next_action=state.next_action,
            human_action_required=state.human_action_required,
            steps=state.steps,
            notes=state.notes,
        )
