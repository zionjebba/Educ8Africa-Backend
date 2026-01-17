
"""Recognition model for Users of the IAxOS system."""

from datetime import datetime, date
from sqlalchemy import Column, Date, String, DateTime, ForeignKey
from app.constants.constants import EventCategory
from app.models.base import Base


class Recognition(Base):
    """Model representing recognitions given to users."""

    __tablename__ = "recognitions"
    recognition_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    team_name = Column(String, nullable=True)
    title = Column(String, nullable=False)
    recognition_type = Column(String, nullable=False)
    date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)