"""Team models for organizational structure."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class Team(Base, TimestampMixin):
    """Model representing teams within departments."""

    __tablename__ = "teams"
    team_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    department_id = Column(String, ForeignKey("departments.department_id"), nullable=False)
    team_lead_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    department = relationship("Department", back_populates="teams")
    team_lead = relationship("User", foreign_keys=[team_lead_id], backref="led_team")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    performance_metrics = relationship("TeamPerformance", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base, TimestampMixin):
    """Model representing team membership."""

    __tablename__ = "team_members"
    membership_id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    role_in_team = Column(String, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    team = relationship("Team", back_populates="members")
    user = relationship("User", backref="team_memberships")


class TeamPerformance(Base, TimestampMixin):
    """Model representing team performance metrics."""

    __tablename__ = "team_performance"
    performance_id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    tasks_assigned = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_overdue = Column(Integer, default=0)
    average_completion_rate = Column(Integer, default=0)
    average_response_time = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)
    total_culture_points = Column(Integer, default=0)
    reports_submitted = Column(Integer, default=0)
    reports_on_time = Column(Integer, default=0)
    team = relationship("Team", back_populates="performance_metrics")