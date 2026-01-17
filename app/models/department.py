
"""Department models for organizational structure."""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    """Model representing departments in the organization."""

    __tablename__ = "departments"
    department_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    mandate = Column(Text, nullable=True)
    head_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    head = relationship("User", foreign_keys=[head_id], backref="headed_department")
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan")
    performance_metrics = relationship("DepartmentPerformance", back_populates="department", cascade="all, delete-orphan")

class DepartmentPerformance(Base, TimestampMixin):
    """Model representing department performance metrics."""

    __tablename__ = "department_performance"
    performance_id = Column(String, primary_key=True, index=True)
    department_id = Column(String, ForeignKey("departments.department_id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_teams = Column(Integer, default=0)
    active_members = Column(Integer, default=0)
    tasks_assigned = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_overdue = Column(Integer, default=0)
    average_completion_rate = Column(Integer, default=0)
    average_response_time = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)
    total_culture_points = Column(Integer, default=0)
    reports_submitted = Column(Integer, default=0)
    reports_on_time = Column(Integer, default=0)
    projects_initiated = Column(Integer, default=0)
    projects_completed = Column(Integer, default=0)
    department = relationship("Department", back_populates="performance_metrics")