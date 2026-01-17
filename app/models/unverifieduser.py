from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.models.base import Base, TimestampMixin


class UnverifiedUser(Base, TimestampMixin):
    __tablename__ = 'unverified_users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    phone = Column(String(20), unique=True)
    otp_secret = Column(String(100), nullable=False)
    otp_expires = Column(DateTime, nullable=False)
    verification_channel = Column(String(10), nullable=False)  # 'email' or 'sms'
    verification_attempts = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    lock_expires = Column(DateTime)
    
    def __repr__(self):
        return f"<UnverifiedUser {self.email or self.phone}>"