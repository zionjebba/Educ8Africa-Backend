import uuid
from sqlalchemy import Column, Index, String, Text, DateTime, Boolean
from datetime import datetime

from app.models.base import Base, TimestampMixin


class ContactMessage(Base, TimestampMixin):
    """Model for contact form submissions."""

    __tablename__ = "contact_messages"

    message_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    authorized_contact = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_replied = Column(Boolean, default=False)

    __table_args__ = (
        Index(
            'idx_contact_duplicate_check',
            'email',
            'subject',
            'submitted_at'
        ),
    )