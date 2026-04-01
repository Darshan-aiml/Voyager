import logging

from fastapi import APIRouter, Depends

from app.api.routes.booking import get_booking_automation_service
from app.api.routes.plan import get_plan_service
from app.models.request import TravelAdvisorRequest
from app.models.response import TravelAdvisorResponse
from app.services.advisor.advisor_service import AdvisorService
from app.services.booking.automation_service import BookingAutomationService
from app.services.planner.plan_service import PlanService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_advisor_service(
    plan_service: PlanService = Depends(get_plan_service),
    booking_automation_service: BookingAutomationService = Depends(get_booking_automation_service),
) -> AdvisorService:
    return AdvisorService(plan_service, booking_automation_service)


@router.post("/travel-advisor/respond", response_model=TravelAdvisorResponse)
async def travel_advisor_respond(
    payload: TravelAdvisorRequest,
    advisor_service: AdvisorService = Depends(get_advisor_service),
) -> TravelAdvisorResponse:
    logger.info("/travel-advisor/respond invoked intent=%s", payload.intent)
    return await advisor_service.respond(payload)
