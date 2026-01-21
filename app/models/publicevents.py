from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.constants.constants import EventStatus, TicketStatus, TicketTier
from app.core.database import Base


class PublicEvent(Base):
    __tablename__ = 'public_events'
    
    id = Column(Integer, primary_key=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "event-axi-launch-2026"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # e.g., "AXI Launch", "App Launch"
    
    # Date and time
    event_date = Column(DateTime, nullable=False)
    event_time = Column(String(50), nullable=False)  # e.g., "9:00 AM"
    event_end_date = Column(DateTime, nullable=True)  # Optional end date
    
    # Location
    venue_name = Column(String(255), nullable=True)
    venue_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="Ghana")
    
    # Media
    image_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    
    # Event details
    status = Column(SQLEnum(EventStatus), default=EventStatus.DRAFT)
    is_published = Column(Boolean, default=False)
    max_attendees = Column(Integer, nullable=True)  # Optional capacity limit
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    ticket_types = relationship("EventTicketType", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("EventTicket", back_populates="event", cascade="all, delete-orphan")

    volunteer_applications = relationship(
        "VolunteerApplication",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    speaker_applications = relationship(
        "SpeakerApplication",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    sponsorship_applications = relationship(
        "SponsorshipApplication",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    partnership_applications = relationship(
        "PartnershipApplication",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<PublicEvent {self.title} - {self.event_date}>"
    
    @property
    def is_sold_out(self):
        """Check if event is sold out"""
        if not self.max_attendees:
            return False
        confirmed_tickets = sum(
            tt.sold_count for tt in self.ticket_types
        )
        return confirmed_tickets >= self.max_attendees
    
    @property
    def tickets_sold(self):
        """Get total tickets sold"""
        return sum(tt.sold_count for tt in self.ticket_types)
    
    @property
    def volunteer_count(self):
        """Get count of volunteer applications"""
        return len(self.volunteer_applications)
    
    @property
    def speaker_count(self):
        """Get count of speaker applications"""
        return len(self.speaker_applications)
    
    @property
    def sponsorship_count(self):
        """Get count of sponsorship applications"""
        return len(self.sponsorship_applications)
    
    @property
    def partnership_count(self):
        """Get count of partnership applications"""
        return len(self.partnership_applications)


class EventTicketType(Base):
    __tablename__ = 'event_ticket_types'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('public_events.id'), nullable=False)
    
    # Ticket type details
    tier = Column(SQLEnum(TicketTier), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Regular", "VIP", "VVIP"
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # In cedis
    
    # Features (stored as JSON or separate features table)
    features = Column(Text, nullable=True)  # JSON string of features
    
    # Availability
    quantity_available = Column(Integer, nullable=True)  # None = unlimited
    quantity_sold = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    
    # Sales period
    sales_start_date = Column(DateTime, nullable=True)
    sales_end_date = Column(DateTime, nullable=True)
    
    # Benefits
    includes_axi_subscription = Column(Boolean, default=True)
    axi_subscription_months = Column(Integer, default=2)
    is_popular = Column(Boolean, default=False)  # Highlight as popular
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("PublicEvent", back_populates="ticket_types")
    tickets = relationship("EventTicket", back_populates="ticket_type")
    
    def __repr__(self):
        return f"<EventTicketType {self.name} - GHS {self.price}>"
    
    @property
    def sold_count(self):
        """Get number of confirmed tickets sold"""
        return self.quantity_sold
    
    @property
    def is_sold_out(self):
        """Check if this ticket type is sold out"""
        if not self.quantity_available:
            return False
        return self.quantity_sold >= self.quantity_available
    
    @property
    def available_quantity(self):
        """Get remaining tickets"""
        if not self.quantity_available:
            return None  # Unlimited
        return max(0, self.quantity_available - self.quantity_sold)


class EventTicket(Base):
    __tablename__ = 'event_tickets'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('public_events.id'), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey('event_ticket_types.id'), nullable=False)
    event_user_id = Column(Integer, ForeignKey('event_users.id'), nullable=False)
    
    # Ticket details
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "AXI2026-VIP-0001"
    qr_code = Column(Text, nullable=True)  # QR code for check-in (can be large base64 string)
    
    # Attendee information
    attendee_name = Column(String(255), nullable=False)
    attendee_email = Column(String(255), nullable=False)
    attendee_phone = Column(String(50), nullable=True)
    
    # Purchase details
    price_paid = Column(Numeric(10, 2), nullable=False)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    # Status
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.PENDING)
    
    # Check-in
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checked_in_by = Column(Integer, ForeignKey('event_users.id'), nullable=True)  # Staff who checked in
    
    # Timestamps
    purchased_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("PublicEvent", back_populates="tickets")
    ticket_type = relationship("EventTicketType", back_populates="tickets")
    event_user = relationship("EventUser", foreign_keys=[event_user_id], back_populates="tickets")
    payment = relationship("Payment", foreign_keys=[payment_id], back_populates="event_tickets")
    checked_in_by_event_user = relationship("EventUser", foreign_keys=[checked_in_by], back_populates="checked_in_tickets")
    
    def __repr__(self):
        return f"<EventTicket {self.ticket_number} - {self.status}>"
    
    def generate_ticket_number(self):
        """Generate a unique ticket number"""
        import random
        import string
        event_code = self.event.slug[:8].upper()
        tier_code = self.ticket_type.tier.value[:4].upper()
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{event_code}-{tier_code}-{random_suffix}"
    
    def confirm_ticket(self):
        """Confirm ticket after successful payment"""
        self.status = TicketStatus.CONFIRMED
        self.confirmed_at = datetime.utcnow()
        # Increment sold count
        self.ticket_type.quantity_sold += 1