from datetime import date
from typing import Optional
from pydantic import BaseModel

from app.constants.constants import EventCategory


class EventResponse(BaseModel):
    event_id: str
    title: str
    description: Optional[str]
    category: EventCategory
    event_date: date
    event_time: str
    max_attendees: int
    attendee_count: int
    
    class Config:
        from_attributes = True

# Pydantic schemas
class RSVPRequest(BaseModel):
    event_id: str
    status: str = "attending"