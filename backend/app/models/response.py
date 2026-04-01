from pydantic import BaseModel


class TravelOption(BaseModel):
    mode: str
    route: str
    price: float
    duration: str
    duration_minutes: int
    reliability: float
    reason: str | None = None
    availability: str | None = None
    booking_url: str | None = None
    external_id: str | None = None


class PlanTripResponse(BaseModel):
    best_option: TravelOption
    fallback_option: TravelOption


class BookingResponse(BaseModel):
    booking_url: str


class BookingWorkflowStep(BaseModel):
    id: str
    title: str
    status: str
    automation_level: str
    human_action_required: bool = False
    details: str | None = None


class BookingWorkflowResponse(BaseModel):
    workflow_id: str
    mode: str
    provider: str
    booking_url: str
    status: str
    next_action: str
    human_action_required: bool
    steps: list[BookingWorkflowStep]
    notes: list[str]
