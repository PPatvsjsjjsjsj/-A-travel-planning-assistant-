from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


BudgetLevel = Literal["经济", "舒适", "品质"]


class TripRequest(BaseModel):
    origin: str = Field(min_length=1, max_length=40)
    destination: str = Field(min_length=1, max_length=40)
    days: int = Field(default=3, ge=1, le=15)
    departure_date: date | None = None
    travelers: int = Field(default=1, ge=1, le=20)
    budget_level: BudgetLevel = "舒适"
    transport_preference: str = Field(default="综合推荐", max_length=30)
    interests: list[str] = Field(default_factory=list, max_length=8)
    notes: str = Field(default="", max_length=500)

    @field_validator("origin", "destination", "transport_preference", mode="before")
    @classmethod
    def clean_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("interests", mode="before")
    @classmethod
    def clean_interests(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item for item in value.replace("，", ",").split(",") if item.strip()]
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    @model_validator(mode="after")
    def locations_must_differ(self):
        if self.origin == self.destination:
            raise ValueError("出发地和目的地不能相同")
        return self


class NaturalTripRequest(BaseModel):
    message: str = Field(min_length=2, max_length=500)


class TransportOption(BaseModel):
    mode: str
    route: str
    duration: str
    departure: str
    arrival: str
    steps: list[str] = Field(default_factory=list)
    advice: str


class ScheduleItem(BaseModel):
    time: str
    activity: str
    location: str
    tips: str = ""


class DayPlan(BaseModel):
    day: int
    title: str
    area: str
    schedule: list[ScheduleItem]
    meals: list[str] = Field(default_factory=list)
    accommodation: str = ""
    daily_cost: str = ""


class BudgetSummary(BaseModel):
    transport: str
    accommodation: str
    food: str
    tickets: str
    local_transit: str
    total: str
    note: str = ""


class TravelPreparation(BaseModel):
    essentials: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    clothing: list[str] = Field(default_factory=list)
    health: list[str] = Field(default_factory=list)
    electronics: list[str] = Field(default_factory=list)
    bookings: list[str] = Field(default_factory=list)
    destination_specific: list[str] = Field(default_factory=list)
    last_check: list[str] = Field(default_factory=list)


class TripPlan(BaseModel):
    title: str
    summary: str
    origin: str
    destination: str
    days: int
    best_for: list[str] = Field(default_factory=list)
    transport_options: list[TransportOption]
    itinerary: list[DayPlan]
    budget: BudgetSummary
    preparation: TravelPreparation
    booking_tips: list[str] = Field(default_factory=list)
    practical_tips: list[str] = Field(default_factory=list)
    source: Literal["deepseek", "local_demo"] = "deepseek"
    notice: str = "行程按常规开放和交通条件规划；出发前 48 小时复查天气、预约状态和临时交通调整。"


class PlanResponse(BaseModel):
    request: TripRequest
    plan: TripPlan
    skills_used: list[str] = Field(default_factory=list)
