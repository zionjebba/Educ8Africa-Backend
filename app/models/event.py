"""Report model for Users of the IAxOS system."""

from datetime import datetime
from sqlalchemy import Column, Date, Integer, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.constants.constants import EventCategory
from app.models.base import Base


class Event(Base):
    """Model representing events organized for users."""

    __tablename__ = "events"
    event_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(EventCategory), nullable=False)
    event_date = Column(Date, nullable=False)
    event_time = Column(String, nullable=False)
    location = Column(String, nullable=True)
    max_attendees = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    rsvps = relationship("EventRSVP", back_populates="event")
    creator = relationship("User", back_populates="created_events", foreign_keys=[created_by])


class EventRSVP(Base):
    __tablename__ = "event_rsvps"
    rsvp_id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    status = Column(String, default="attending")
    created_at = Column(DateTime, default=datetime.utcnow)
    event = relationship("Event", back_populates="rsvps")
    user = relationship("User", back_populates="event_rsvps")