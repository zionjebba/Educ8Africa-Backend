import datetime
from typing import Optional, List
from pydantic import BaseModel


class OnboardingRequest(BaseModel):
    education_role: str
    learning_goals: Optional[str] = None
    subjects_of_interest: List[str]
    experience_level: Optional[str] = None


class OnboardingResponseSchema(BaseModel):
    response_id: str
    user_id: str
    total_score: int
    points_earned: int
    completed_at: datetime.datetime

    class Config:
        from_attributes = True
