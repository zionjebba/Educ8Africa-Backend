from typing import Optional

from pydantic import BaseModel


class ProfileUpdateRequest(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[str] = None
    linkedin_url: Optional[str] = None
    booking_link: Optional[str] = None