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
