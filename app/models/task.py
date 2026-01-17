"""Tasks model for the Users of IAxOS system."""

from sqlalchemy import Column, Text, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.constants.constants import TaskStatus
from app.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    """Model representing tasks assigned to users."""

    __tablename__ = "tasks"
    task_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    milestone_id = Column(String, ForeignKey("milestones.milestone_id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.pending)
    category = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="tasks")
    milestone = relationship("Milestone", back_populates="tasks")
    report = relationship(
        "Report", 
        back_populates="task",
        uselist=False
    )