from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal

from app.constants.constants import EventStatus, TicketStatus, TicketTier


# ==================== EVENT SCHEMAS ====================

class EventCreate(BaseModel):
    slug: str = Field(..., max_length=255)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    category: str = Field(..., max_length=100)
    
    event_date: datetime
    event_time: str = Field(..., max_length=50)
    event_end_date: Optional[datetime] = None
    
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="Ghana", max_length=100)
    
    image_url: Optional[str] = Field(None, max_length=500)
    banner_url: Optional[str] = Field(None, max_length=500)
    
    status: EventStatus = EventStatus.DRAFT
    is_published: bool = False
    max_attendees: Optional[int] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    
    event_date: Optional[datetime] = None
    event_time: Optional[str] = Field(None, max_length=50)
    event_end_date: Optional[datetime] = None
    
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    
    image_url: Optional[str] = Field(None, max_length=500)
    banner_url: Optional[str] = Field(None, max_length=500)
    
    status: Optional[EventStatus] = None
    is_published: Optional[bool] = None
    max_attendees: Optional[int] = None


class EventTicketTypeResponse(BaseModel):
    id: int
    event_id: int
    tier: TicketTier
    name: str
    description: Optional[str] = None
    price: Decimal
    features: Optional[str] = None
    
    quantity_available: Optional[int] = None
    quantity_sold: int
    is_available: bool
    
    sales_start_date: Optional[datetime] = None
    sales_end_date: Optional[datetime] = None
    
    includes_axi_subscription: bool
    axi_subscription_months: int
    is_popular: bool
    
    sold_count: int
    is_sold_out: bool
    available_quantity: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str] = None
    category: str
    
    event_date: datetime
    event_time: str
    event_end_date: Optional[datetime] = None
    
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    city: Optional[str] = None
    country: str
    
    image_url: Optional[str] = None
    banner_url: Optional[str] = None
    
    status: EventStatus
    is_published: bool
    max_attendees: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    
    is_sold_out: bool
    tickets_sold: int
    
    ticket_types: List[EventTicketTypeResponse] = []
    
    class Config:
        from_attributes = True


# ==================== TICKET TYPE SCHEMAS ====================

class EventTicketTypeCreate(BaseModel):
    event_id: int
    tier: TicketTier
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    features: Optional[str] = None
    
    quantity_available: Optional[int] = Field(None, gt=0)
    is_available: bool = True
    
    sales_start_date: Optional[datetime] = None
    sales_end_date: Optional[datetime] = None
    
    includes_axi_subscription: bool = True
    axi_subscription_months: int = Field(default=2, ge=0)
    is_popular: bool = False


# ==================== TICKET PURCHASE SCHEMAS ====================

class TicketPurchaseRequest(BaseModel):
    event_id: int
    ticket_type_id: int
    quantity: int = Field(..., ge=1, le=10)
    
    attendee_name: str = Field(..., max_length=255)
    attendee_email: EmailStr
    attendee_phone: Optional[str] = Field(None, max_length=50)
    
    callback_url: str = Field(..., max_length=500)
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        if v > 10:
            raise ValueError('Maximum 10 tickets per purchase')
        return v


# ==================== TICKET SCHEMAS ====================

class EventTicketResponse(BaseModel):
    id: int
    event_id: int
    ticket_type_id: int
    user_id: int
    
    ticket_number: str
    qr_code: Optional[str] = None
    
    attendee_name: str
    attendee_email: str
    attendee_phone: Optional[str] = None
    
    price_paid: Decimal
    payment_reference: Optional[str] = None
    
    status: TicketStatus
    
    checked_in: bool
    checked_in_at: Optional[datetime] = None
    
    purchased_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== CHECK-IN SCHEMAS ====================

class TicketCheckInRequest(BaseModel):
    ticket_number: str = Field(..., max_length=50)


class TicketCheckInResponse(BaseModel):
    success: bool
    message: str
    ticket: Optional[EventTicketResponse] = None


# ==================== STATISTICS SCHEMAS ====================

class EventStatistics(BaseModel):
    total_tickets_sold: int
    total_revenue: Decimal
    tickets_by_tier: Dict[str, int]
    check_in_count: int
    check_in_percentage: float

class TicketQRVerifyRequest(BaseModel):
    ticket_number: str
    event_id: int
    email: str
    name: str
    type: str