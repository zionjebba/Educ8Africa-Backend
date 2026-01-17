import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """Model for in-app notifications."""
    
    __tablename__ = "notifications"
    
    notification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="linkedin_post")  # linkedin_post, task, event, etc.
    
    # Action link
    action_url = Column(String, nullable=True)  # Link to LinkedIn post or internal page
    action_label = Column(String, nullable=True)  # "View Post", "Engage Now", etc.
    
    # Metadata
    reference_id = Column(String, nullable=True)  # post_id, task_id, etc.
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")