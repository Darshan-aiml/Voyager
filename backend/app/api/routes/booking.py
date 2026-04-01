import logging

from fastapi import APIRouter, Depends

from app.models.request import (
    BookingWorkflowActionRequest,
    StartAutomatedBookingRequest,
    StartBookingRequest,
)
from app.models.response import BookingResponse, BookingWorkflowResponse
from app.services.booking.automation_service import BookingAutomationService
from app.services.booking.booking_service import BookingService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_booking_service() -> BookingService:
    return BookingService()


def get_booking_automation_service(
    booking_service: BookingService = Depends(get_booking_service),
) -> BookingAutomationService:
    return BookingAutomationService(booking_service)


@router.post("/start-booking", response_model=BookingResponse)
async def start_booking(
    payload: StartBookingRequest,
    booking_service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    logger.info("/start-booking invoked for mode=%s", payload.mode)
    booking_url = await booking_service.get_booking_url(
        mode=payload.mode,
        source=payload.source,
        destination=payload.destination,
        travel_date=payload.date,
        external_id=payload.external_id,
    )
    return BookingResponse(booking_url=booking_url)


@router.post("/automate-booking", response_model=BookingWorkflowResponse)
async def automate_booking(
    payload: StartAutomatedBookingRequest,
    automation_service: BookingAutomationService = Depends(get_booking_automation_service),
) -> BookingWorkflowResponse:
    logger.info("/automate-booking invoked for mode=%s", payload.mode)
    return await automation_service.start_workflow(payload)


@router.get("/booking-workflows/{workflow_id}", response_model=BookingWorkflowResponse)
async def get_booking_workflow(
    workflow_id: str,
    automation_service: BookingAutomationService = Depends(get_booking_automation_service),
) -> BookingWorkflowResponse:
    logger.info("/booking-workflows/%s requested", workflow_id)
    return await automation_service.get_workflow(workflow_id)


@router.post("/booking-workflows/{workflow_id}/actions", response_model=BookingWorkflowResponse)
async def update_booking_workflow(
    workflow_id: str,
    payload: BookingWorkflowActionRequest,
    automation_service: BookingAutomationService = Depends(get_booking_automation_service),
) -> BookingWorkflowResponse:
    logger.info("/booking-workflows/%s/actions invoked action=%s", workflow_id, payload.action)
    return await automation_service.apply_action(workflow_id, payload)
