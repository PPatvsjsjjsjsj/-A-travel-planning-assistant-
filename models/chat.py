from typing import Literal

from pydantic import BaseModel, Field

from models.trip import TripPlan, TripRequest


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=800)
    session_id: str | None = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    stage: Literal["collecting", "answering", "planned", "updated", "error"]
    plan: TripPlan | None = None
    request: TripRequest | None = None
    skills_used: list[str] = Field(default_factory=list)
    quick_replies: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]
    request: TripRequest | None = None
    plan: TripPlan | None = None
    skills_used: list[str] = Field(default_factory=list)
