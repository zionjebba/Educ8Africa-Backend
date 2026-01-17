"""SocialMatch model for Users of the IAxOS system."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base


def utc_now():
    """Return current UTC time as naive datetime for database storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SocialMatch(Base):
    """Model representing social matches between users for networking."""

    __tablename__ = "social_matches"
    
    match_id = Column(String, primary_key=True, index=True)
    user1_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    user2_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    match_date = Column(Date, nullable=False)
    common_interests = Column(Text, nullable=True)
    video_call_link = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    
    # Draw number to distinguish between first and second Sunday draws
    draw_number = Column(Integer, nullable=True, comment="1 for first draw, 2 for second draw")
    
    # Rating fields for each user
    user1_rating = Column(Integer, nullable=True, comment="Rating from user1 (1-5)")
    user2_rating = Column(Integer, nullable=True, comment="Rating from user2 (1-5)")
    user1_feedback = Column(Text, nullable=True, comment="Optional feedback from user1")
    user2_feedback = Column(Text, nullable=True, comment="Optional feedback from user2")
    user1_ended_at = Column(DateTime, nullable=True, comment="When user1 ended the call")
    user2_ended_at = Column(DateTime, nullable=True, comment="When user2 ended the call")
    
    # Use custom function instead of datetime.utcnow (which is deprecated)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    user1 = relationship(
        "User", 
        back_populates="social_matches_as_user1", 
        foreign_keys=[user1_id]
    )
    user2 = relationship(
        "User", 
        back_populates="social_matches_as_user2", 
        foreign_keys=[user2_id]
    )
    
    def __repr__(self):
        draw_info = f" (Draw {self.draw_number})" if self.draw_number else ""
        return f"<SocialMatch {self.match_id}: {self.user1_id} & {self.user2_id}{draw_info}>"
    
    @property
    def is_fully_rated(self):
        """Check if both users have provided ratings."""
        return self.user1_rating is not None and self.user2_rating is not None
    
    @property
    def average_rating(self):
        """Calculate average rating if both users have rated."""
        if self.is_fully_rated:
            return (self.user1_rating + self.user2_rating) / 2
        return None