"""User model for the IAxOS system - Updated with Department/Team, CEO Message, and Google Auth."""

import uuid
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.constants.constants import UserRole, FounderChoice
from app.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    microsoft_id = Column(String, unique=True, nullable=True, index=True)  # Keep
    # google_id removed
    avatar = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    department_id = Column(String, ForeignKey("departments.department_id"), nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    skills = Column(Text, nullable=True)
    linkedin_url = Column(String, nullable=True)
    booking_link = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_skipped = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    points = Column(Integer, default=0)
    culture_points = Column(Integer, default=0)
    onboarding_points = Column(Integer, default=0)
    onboarding_completed_at = Column(DateTime, nullable=True)
    onboarding_score = Column(Integer, default=0)
    favourite_founder = Column(Enum(FounderChoice), nullable=True)
    custom_founder_preference = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    has_read_ceo_message = Column(Boolean, default=False)
    has_seen_whats_new = Column(Boolean, default=False)
    last_seen_draw_at = Column(DateTime, nullable=True)
    profile_points_awarded = Column(Boolean, default=False, nullable=False)
    profile_completion_points = Column(Integer, default=0, nullable=False)

    # Relationships
    department = relationship("Department", foreign_keys=[department_id], backref="members")
    tasks = relationship("Task", back_populates="user")
    reports = relationship("Report", back_populates="user", foreign_keys="[Report.user_id]")
    reviewed_reports = relationship("Report", back_populates="reviewer", foreign_keys="[Report.reviewed_by]")
    leave_requests = relationship("LeaveRequest", back_populates="user", foreign_keys="[LeaveRequest.user_id]")
    approved_leave_requests = relationship("LeaveRequest", back_populates="approver", foreign_keys="[LeaveRequest.approved_by]")
    event_rsvps = relationship("EventRSVP", back_populates="user")
    created_events = relationship("Event", back_populates="creator", foreign_keys="[Event.created_by]")
    social_matches_as_user1 = relationship("SocialMatch", back_populates="user1", foreign_keys="[SocialMatch.user1_id]")
    social_matches_as_user2 = relationship("SocialMatch", back_populates="user2", foreign_keys="[SocialMatch.user2_id]")
    onboarding_data = relationship("OnboardingResponse", back_populates="user", uselist=False)
    submitted_leadership_reports = relationship("LeadershipReport", back_populates="submitter", foreign_keys="LeadershipReport.submitted_by")
    received_leadership_reports = relationship("LeadershipReport", back_populates="reviewer", foreign_keys="LeadershipReport.submitted_to")
   # Messaging relationships (FIXED)
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )

    received_messages = relationship(
        "Message",
        foreign_keys="Message.recipient_id",
        back_populates="recipient",
        cascade="all, delete-orphan"
    )


    activities = relationship(
        "Activity",
        back_populates="user",
        cascade="all, delete-orphan"
    )
