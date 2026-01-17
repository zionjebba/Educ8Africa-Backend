from typing import Optional
from pydantic import BaseModel

from app.constants.constants import FounderChoice
from app.constants.constants import FounderChoice
from app.schemas.userSchema import UserResponse


class LeaderboardEntry(BaseModel):
    rank: int
    user: UserResponse
    score: float
    activities: int
    trend: str
    
    class Config:
        from_attributes = True

class FounderInspirationResponse(BaseModel):
    inspiration_id: str
    founder: FounderChoice
    title: str
    content: str
    quote: Optional[str]
    image_url: Optional[str]
    
    class Config:
        from_attributes = True