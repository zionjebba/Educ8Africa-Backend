import uuid
from sqlalchemy import Column, Index, String, DateTime, Boolean
from datetime import datetime

from app.models.base import Base, TimestampMixin


class JobWaitlist(Base, TimestampMixin):
    """Model for job opportunity waitlist."""

    __tablename__ = "job_waitlist"

    waitlist_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    linkedin_url = Column(String, nullable=True)
    preferred_role = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)  # Track if user has been notified of a role
    is_active = Column(Boolean, default=True)  # Allow users to be marked inactive if they unsubscribe

    __table_args__ = (
        Index(
            'idx_waitlist_duplicate_check',
            'email',
            'submitted_at'
        ),
        Index(
            'idx_waitlist_active',
            'is_active',
            'notified'
        ),
    )
