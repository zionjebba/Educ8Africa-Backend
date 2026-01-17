"""Milestone model for team weekly goals."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Milestone(Base, TimestampMixin):
    """Model representing weekly team milestones."""

    __tablename__ = "milestones"
    milestone_id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)
    created_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    team = relationship("Team", backref="milestones")
    creator = relationship("User", foreign_keys=[created_by], backref="created_milestones")
    tasks = relationship("Task", back_populates="milestone")