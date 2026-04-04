from datetime import date as dt_date
from typing import Literal

from pydantic import BaseModel, Field


TripPreference = Literal["cheap", "comfort", "luxury"]


class TravelSlotState(BaseModel):
    source: str | None = Field(default=None, min_length=2)
    destination: str | None = Field(default=None, min_length=2)
    date: dt_date | str | None = None
    people: int | None = Field(default=None, ge=1)
    days: int | None = Field(default=None, ge=1, le=30)
    preference: TripPreference | None = None


class TravelPlanRequest(BaseModel):
    query: str | None = Field(default=None, min_length=3, description="Natural-language trip planning request")
    source: str | None = Field(default=None, min_length=2)
    destination: str | None = Field(default=None, min_length=2)
    date: dt_date | str | None = None
    people: int | None = Field(default=None, ge=1)
    days: int | None = Field(default=None, ge=1, le=30)
    preference: TripPreference | None = None
    slot_state: TravelSlotState | None = None
