# models/messaging.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Direct messages between users"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    sender_id = Column(String, ForeignKey('users.user_id'), nullable=False)  # Changed to user_id
    recipient_id = Column(String, ForeignKey('users.user_id'), nullable=False)  # Changed to user_id
    
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")


class Activity(Base, TimestampMixin):
    """User activities/posts on the platform"""
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)  # Changed to user_id
    
    activity_type = Column(String(50), nullable=False)  # post, milestone, announcement
    content = Column(Text, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="activities")