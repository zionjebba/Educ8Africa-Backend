"""Leave application model for Users of the IAxOS system."""

from datetime import datetime
from sqlalchemy import Column, Date, ForeignKey, String, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from app.constants.constants import LeaveType, RequestStatus
from app.models.base import Base


class LeaveRequest(Base):
    """Model representing leave requests submitted by users."""

    __tablename__ = "leave_requests"
    request_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    approved_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="leave_requests", foreign_keys=[user_id])
    approver = relationship("User", back_populates="approved_leave_requests", foreign_keys=[approved_by])