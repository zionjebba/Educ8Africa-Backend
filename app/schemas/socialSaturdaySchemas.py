from typing import Optional
from pydantic import BaseModel, Field


class CallRatingRequest(BaseModel):
    """Request model for rating a social call."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback: Optional[str] = Field(None, max_length=500, description="Optional feedback")
