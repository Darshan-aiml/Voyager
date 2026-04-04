from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractTripRequest(BaseModel):
    text: str = Field(..., min_length=2, description="Raw conversational text from the user")


class TripExtractionData(BaseModel):
    source: str | None = None
    destination: str | None = None
    date: str | None = None
    days: int | None = Field(default=None, ge=1, le=30)
    people: int | None = Field(default=None, ge=1, le=20)
    preference: str | None = Field(default=None, pattern="^(cheap|comfort|luxury)$")


class ExtractTripResponse(TripExtractionData):
    raw_text: str
