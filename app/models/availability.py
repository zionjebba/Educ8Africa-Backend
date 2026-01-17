from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.constants.constants import AvailabilityCheckStatus
from app.models.base import Base, TimestampMixin


class AvailabilityCheckSchedule(Base, TimestampMixin):
    """Master schedule for when availability checks are sent"""

    __tablename__ = "availability_check_schedules"
    schedule_id = Column(String, primary_key=True, index=True)    
    check_date = Column(Date, nullable=False, index=True)
    check_time = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False)
    total_employees = Column(Integer, default=0)
    total_confirmed = Column(Integer, default=0)
    total_missed = Column(Integer, default=0)
    total_late = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    responses = relationship("AvailabilityCheckResponse", back_populates="schedule")


class AvailabilityCheckResponse(Base, TimestampMixin):
    """Individual employee responses to availability checks"""

    __tablename__ = "availability_check_responses"
    response_id = Column(String, primary_key=True, index=True)
    schedule_id = Column(String, ForeignKey("availability_check_schedules.schedule_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    status = Column(SQLEnum(AvailabilityCheckStatus), default=AvailabilityCheckStatus.pending)
    responded_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Integer, nullable=True)
    points_earned = Column(Integer, default=0)
    points_deducted = Column(Integer, default=0)
    ip_address = Column(String, nullable=True)
    device_info = Column(String, nullable=True)
    schedule = relationship("AvailabilityCheckSchedule", back_populates="responses")


class AvailabilityStats(Base, TimestampMixin):
    """Track employee availability statistics over time"""

    __tablename__ = "availability_stats"
    stat_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)
    total_checks_sent = Column(Integer, default=0)
    total_confirmed = Column(Integer, default=0)
    total_missed = Column(Integer, default=0)
    total_late = Column(Integer, default=0)
    confirmation_rate = Column(Float, default=0.0)
    average_response_time = Column(Float, default=0.0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)
    total_points_lost = Column(Integer, default=0)