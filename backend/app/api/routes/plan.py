import logging

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.request import PlanTripRequest
from app.models.response import PlanTripResponse
from app.services.planner.plan_service import PlanService
from app.services.transport.bus_service import BusService
from app.services.transport.flight_service import FlightService
from app.services.transport.train_service import TrainService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_plan_service(settings: Settings = Depends(get_settings)) -> PlanService:
    return PlanService(
        settings=settings,
        train_service=TrainService(settings),
        flight_service=FlightService(settings),
        bus_service=BusService(),
    )


@router.post("/plan-trip", response_model=PlanTripResponse)
async def plan_trip(
    payload: PlanTripRequest,
    plan_service: PlanService = Depends(get_plan_service),
) -> PlanTripResponse:
    logger.info("/plan-trip invoked for %s -> %s", payload.source, payload.destination)
    return await plan_service.plan_trip(
        source=payload.source,
        destination=payload.destination,
        travel_date=payload.date,
        budget=payload.budget,
    )
