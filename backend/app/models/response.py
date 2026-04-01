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


class BrowserAutomationStub(BaseModel):
    provider: str
    runner_name: str
    script_path: str
    browser: str
    launch_mode: str
    current_target_url: str
    supported_actions: list[str]
    checkpoint_labels: list[str]
    next_stub_instruction: str
    notes: list[str]


class BookingAutomationExecutionResponse(BaseModel):
    workflow_id: str
    provider: str
    mode: str
    action: str
    status: str
    current_url: str | None = None
    page_title: str | None = None
    message: str
    requires_human_action: bool
    next_action: str
    browser_automation: BrowserAutomationStub
    notes: list[str]


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
    browser_automation: BrowserAutomationStub
