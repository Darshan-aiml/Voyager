from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TravelStyle = Literal["budget", "comfort", "fast"]


class TravelPreferences(BaseModel):
    budget: float = Field(..., ge=0)
    travel_style: TravelStyle
    people: int = Field(..., ge=1)
    days: int = Field(..., ge=1)


class TravelRecommendation(BaseModel):
    mode: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    duration: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


class ItineraryItem(BaseModel):
    day: int = Field(..., ge=1)
    plan: str = Field(..., min_length=1)


class TravelPlanData(BaseModel):
    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    preferences: TravelPreferences
    best_option: TravelRecommendation
    alternatives: list[TravelRecommendation] = Field(default_factory=list)
    itinerary: list[ItineraryItem] = Field(default_factory=list)
    insight: str = Field(..., min_length=1)
    booking_url: str = Field(..., min_length=1)


class TravelPlanApiResponse(BaseModel):
    text_response: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    data: TravelPlanData


class IncompletePlanResponse(BaseModel):
    status: Literal["incomplete"]
    missing_field: Literal["source", "destination", "date", "people", "days", "preference"]
    slot_state: dict


class CompletePlanResponse(BaseModel):
    status: Literal["complete"]
    data: TravelPlanData
