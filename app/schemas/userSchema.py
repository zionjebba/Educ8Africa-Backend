from typing import Optional
from pydantic import BaseModel, EmailStr

from app.constants.constants import UserRole


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    first_name: str
    last_name: str
    avatar: Optional[str]
    role: UserRole
    department: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    onboarding_completed: bool
    is_active: bool
    points: int
    culture_points: int
    onboarding_points: int
    
    class Config:
        from_attributes = True