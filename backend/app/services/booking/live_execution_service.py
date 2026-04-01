from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status

from app.models.request import ExecuteBookingAutomationRequest, StartAutomatedBookingRequest
from app.models.response import BookingAutomationExecutionResponse


@dataclass
class BrowserExecutionResult:
    status: str
    message: str
    current_url: str | None
    page_title: str | None
    requires_human_action: bool
    notes: list[str]


class BrowserAutomationRunner(Protocol):
    async def run(
        self,
        *,
        payload: StartAutomatedBookingRequest,
        booking_url: str,
        action: str,
        request: ExecuteBookingAutomationRequest,
    ) -> BrowserExecutionResult: ...


class NotImplementedAutomationRunner:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    async def run(
        self,
        *,
        payload: StartAutomatedBookingRequest,
        booking_url: str,
        action: str,
        request: ExecuteBookingAutomationRequest,
    ) -> BrowserExecutionResult:
        return BrowserExecutionResult(
            status="not_implemented",
            message=f"Live browser automation is not implemented yet for {self.provider_name}.",
            current_url=booking_url,
            page_title=None,
            requires_human_action=False,
            notes=[
                "Train and flight still use the workflow skeleton only.",
                "RedBus is the first provider with live Playwright execution support.",
            ],
        )


ACTION_TO_WORKFLOW_EVENT = {
    "search_and_select": "confirm_search_results",
    "fill_traveller_details": "provide_traveller_details",
    "verify_user": "submit_otp",
    "payment": "authorize_payment",
    "complete_booking": "complete",
}


def resolve_requested_action(
    workflow_next_action: str, request: ExecuteBookingAutomationRequest
) -> str:
    action = request.action or workflow_next_action
    if action == "none":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking workflow is already complete.",
        )
    return action

