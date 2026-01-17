from typing import Optional
from pydantic import BaseModel, EmailStr


class ContactMessageRequest(BaseModel):
    """Request schema for contact form submission."""
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    subject: str
    message: str
    authorized_contact: bool = False


class ContactMessageResponse(BaseModel):
    """Response schema for contact form submission."""
    message: str
    message_id: str