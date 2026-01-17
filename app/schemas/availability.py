from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from app.constants.constants import AvailabilityCheckStatus


class AvailabilityCheckScheduleResponse(BaseModel):
    schedule_id: str
    check_date: date
    check_time: datetime
    deadline: datetime
    total_employees: int
    total_confirmed: int
    total_missed: int
    total_late: int
    
    class Config:
        from_attributes = True


class AvailabilityCheckResponseSchema(BaseModel):
    response_id: str
    user_id: str
    status: AvailabilityCheckStatus
    responded_at: Optional[datetime]
    response_time_seconds: Optional[int]
    points_earned: int
    points_deducted: int
    
    class Config:
        from_attributes = True


class AvailabilityStatsResponse(BaseModel):
    user_id: str
    total_checks_sent: int
    total_confirmed: int
    total_missed: int
    total_late: int
    confirmation_rate: float
    average_response_time: float
    current_streak: int
    longest_streak: int
    total_points_earned: int
    total_points_lost: int
    
    class Config:
        from_attributes = True


class ConfirmAvailabilityRequest(BaseModel):
    """Request body when employee confirms availability"""
    schedule_id: str
    device_info: Optional[str] = None