from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class EventUser(Base):
    """Separate user model for event attendees/purchasers"""
    __tablename__ = 'event_users'
    
    id = Column(Integer, primary_key=True)
    
    # User details
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    
    # Optional profile info
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_purchase_at = Column(DateTime, nullable=True)
    
    # Relationships
    tickets = relationship("EventTicket", back_populates="event_user", foreign_keys="EventTicket.event_user_id")
    payments = relationship("Payment", back_populates="event_user", foreign_keys="Payment.event_user_id")
    checked_in_tickets = relationship("EventTicket", back_populates="checked_in_by_event_user", foreign_keys="EventTicket.checked_in_by")
    
    def __repr__(self):
        return f"<EventUser {self.email} - {self.full_name}>"
    
    @property
    def total_tickets_purchased(self):
        """Get total number of tickets purchased"""
        return len(self.tickets)
    
    @property
    def total_amount_spent(self):
        """Get total amount spent on tickets"""
        from app.models.payment import PaymentStatus
        return sum(
            payment.amount for payment in self.payments 
            if payment.status == PaymentStatus.COMPLETED
        )