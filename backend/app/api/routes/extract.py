import logging

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.trip_extraction import ExtractTripRequest, ExtractTripResponse
from app.services.planner.trip_extractor import TripExtractor

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trip_extractor(settings: Settings = Depends(get_settings)) -> TripExtractor:
    return TripExtractor(settings=settings)


@router.post("/extract-trip", response_model=ExtractTripResponse)
async def extract_trip(
    payload: ExtractTripRequest,
    trip_extractor: TripExtractor = Depends(get_trip_extractor),
) -> ExtractTripResponse:
    logger.info("/extract-trip invoked text=%s", payload.text)
    return await trip_extractor.extract(payload.text)
