from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OnboardingSubmit(BaseModel):
    selected_role: str
    selected_team_id: Optional[str] = None
    mission_text: str
    avatar_url: Optional[str] = None


class OnboardingResponseSchema(BaseModel):
    response_id: str
    user_id: str
    selected_role: Optional[str]
    selected_team_id: Optional[str]
    mission_text: Optional[str]
    avatar_url: Optional[str]
    total_score: int
    points_earned: int
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class OnboardingStatusSchema(BaseModel):
    completed: bool
    skipped: bool
    score: Optional[int]
    points_earned: Optional[int]
    completed_at: Optional[datetime]
    details: Optional[OnboardingResponseSchema]
