from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class JobWaitlistRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    linkedin_url: Optional[str] = None
    preferred_role: str

    class Config:
        from_attributes = True


class JobWaitlistResponse(BaseModel):
    message: str
    waitlist_id: str