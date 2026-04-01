from datetime import date

from pydantic import BaseModel, Field


class PlanTripRequest(BaseModel):
    source: str = Field(..., min_length=2, description="Source city")
    destination: str = Field(..., min_length=2, description="Destination city")
    date: date
    budget: float = Field(..., gt=0)


class StartBookingRequest(BaseModel):
    mode: str = Field(..., pattern="^(train|flight|bus)$")
    source: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    date: date
    external_id: str | None = None
