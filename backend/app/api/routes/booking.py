import logging

from fastapi import APIRouter, Depends

from app.models.request import StartBookingRequest
from app.models.response import BookingResponse
from app.services.booking.booking_service import BookingService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_booking_service() -> BookingService:
    return BookingService()


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
