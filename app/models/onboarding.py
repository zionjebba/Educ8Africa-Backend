
"""Onboarding model for the Users of IAxOS system."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.constants.constants import FounderChoice
from app.models.base import Base, TimestampMixin


class OnboardingResponse(Base, TimestampMixin):
    """Model representing onboarding responses for users."""

    __tablename__ = "onboarding_responses"
    response_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)
    ceo_initials_answer = Column(String, nullable=True)
    ceo_initials_correct = Column(Boolean, default=False)
    favourite_founder = Column(SQLEnum(FounderChoice), nullable=True)
    custom_founder_preference = Column(String, nullable=True)
    mission_vision_choice = Column(String, nullable=True)
    mission_vision_correct = Column(Boolean, default=False)
    total_score = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="onboarding_data")
