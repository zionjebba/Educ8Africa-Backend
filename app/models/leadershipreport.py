"""Leadership Report model for Team Leads and Department Leads."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.constants.constants import RequestStatus
from app.models.base import Base, TimestampMixin


class LeadershipReport(Base, TimestampMixin):
    """Model representing reports submitted by team leads and department leads."""

    __tablename__ = "leadership_reports"
    report_id = Column(String, primary_key=True, index=True)
    submitted_by = Column(String, ForeignKey("users.user_id"), nullable=False)  
    submitted_to = Column(String, ForeignKey("users.user_id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.task_id"), nullable=True)
    title = Column(String, nullable=False)
    document_link = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    report_period = Column(String, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    submitter = relationship("User", back_populates="submitted_leadership_reports", foreign_keys=[submitted_by])
    reviewer = relationship("User", back_populates="received_leadership_reports", foreign_keys=[submitted_to])
    task = relationship("Task")