"""Report model for Users of the IAxOS system."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.constants.constants import RequestStatus
from app.models.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    """Model representing reports submitted by users."""

    __tablename__ = "reports"
    report_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.task_id"), nullable=True, unique=True)
    document_link = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    reviewer = relationship("User", back_populates="reviewed_reports", foreign_keys=[reviewed_by])
    task = relationship("Task", back_populates="report")