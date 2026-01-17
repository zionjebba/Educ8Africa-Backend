"""Onboarding model for Educ8Africa users."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class OnboardingResponse(Base, TimestampMixin):
    __tablename__ = "onboarding_responses"

    response_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)

    # Educ8Africa onboarding answers
    education_role = Column(String, nullable=True)  # Student, Teacher, Parent, Admin
    learning_goals = Column(Text, nullable=True)
    subjects_of_interest = Column(Text, nullable=True)  # comma-separated
    experience_level = Column(String, nullable=True)

    # Scoring (KEEP — system feature)
    total_score = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="onboarding_data")
