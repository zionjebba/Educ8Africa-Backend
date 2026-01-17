
"""FounderInspiration model for storing daily inspirational quotes/facts about founders."""

from datetime import datetime
from sqlalchemy import Column, Date, String, DateTime, Text, Enum as SQLEnum
from app.constants.constants import FounderChoice
from app.models.base import Base


class FounderInspiration(Base):
    """Model representing inspirational content related to founders."""

    __tablename__ = "founder_inspirations"
    inspiration_id = Column(String, primary_key=True, index=True)
    founder = Column(SQLEnum(FounderChoice), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    quote = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    date_used = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
