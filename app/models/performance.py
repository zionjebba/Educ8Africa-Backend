
"""Performance model for Users of the IAxOS system."""

from datetime import datetime
from sqlalchemy import Column, Date, Float, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.constants.constants import EventCategory
from app.models.base import Base


class PerformanceMetric(Base):
    """Model representing performance metrics of users."""

    __tablename__ = "performance_metrics"
    metric_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    average_score = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    on_time_rate = Column(Float, default=0.0)
    tasks_completed = Column(Integer, default=0)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)