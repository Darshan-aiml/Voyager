from __future__ import annotations

from datetime import date as dt_date

from pydantic import BaseModel, Field


class PlanTripRequest(BaseModel):
    source: str = Field(..., min_length=2, description="Source city")
    destination: str = Field(..., min_length=2, description="Destination city")
    date: dt_date
    budget: float = Field(..., gt=0)


class StartBookingRequest(BaseModel):
    mode: str = Field(..., pattern="^(train|flight|bus)$")
    source: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    date: dt_date
    external_id: str | None = None


class PassengerDetails(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=120)
    gender: str = Field(..., pattern="^(male|female|other)$")


class ContactDetails(BaseModel):
    phone: str = Field(..., min_length=8)
    email: str = Field(..., min_length=5)


class BookingPreferences(BaseModel):
    seat_preference: str | None = None
    coach_preference: str | None = None
    cabin_class: str | None = None
    boarding_point: str | None = None
    drop_point: str | None = None


class StartAutomatedBookingRequest(BaseModel):
    mode: str = Field(..., pattern="^(train|flight|bus)$")
    source: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    date: dt_date
    external_id: str | None = None
    passengers: list[PassengerDetails] = Field(..., min_length=1)
    contact: ContactDetails
    preferences: BookingPreferences | None = None
    user_confirmed_itinerary: bool = Field(
        ..., description="Voice agent should only start automation after user confirms the trip option."
    )
    payment_authorized: bool = Field(
        default=False,
        description="Set true only after the user explicitly authorizes entering the payment phase.",
    )


class BookingWorkflowActionRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(confirm_search_results|provide_traveller_details|submit_otp|authorize_payment|complete|fail)$",
    )
    note: str | None = None


class ExecuteBookingAutomationRequest(BaseModel):
    headless: bool = False
    timeout_ms: int = Field(default=45000, ge=1000, le=180000)
    action: str | None = Field(
        default=None,
        pattern="^(search_and_select|fill_traveller_details|verify_user|payment|complete_booking)$",
    )


class ExecuteBookingRequest(BaseModel):
    source: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    date: dt_date | None = None


class TravelAdvisorRequest(BaseModel):
    intent: str = Field(
        ...,
        pattern="^(plan_trip|explain_fallback|booking_status|booking_next_step|general_guidance)$",
    )
    user_message: str = Field(..., min_length=3)
    source: str | None = Field(default=None, min_length=2)
    destination: str | None = Field(default=None, min_length=2)
    date: dt_date | None = None
    budget: float | None = Field(default=None, gt=0)
    workflow_id: str | None = None
