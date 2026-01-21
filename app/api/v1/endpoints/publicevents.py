import traceback
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, func
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
import qrcode
import io
import base64

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.eventuser import EventUser
from app.models.publicevents import PublicEvent, EventTicketType, EventTicket
from app.constants.constants import ADMIN_EMAILS, TicketStatus, TicketTier
from app.models.payment import Payment, PaymentStatus, PaymentPurpose
from app.models.user import User
from app.schemas.events import (
    EventCreate, EventUpdate, EventResponse, 
    EventTicketTypeCreate, EventTicketTypeResponse,
    TicketPurchaseRequest, EventTicketResponse,
    TicketCheckInRequest, TicketCheckInResponse,
    EventStatistics, TicketQRVerifyRequest
)
from app.schemas.paymentSchema import PaymentInitRequest
from app.services.EventQRCodeGenerator import generate_event_qr_code_with_logo
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.services.EventApplicationConfirmationEmail import notify_admin_new_ticket_purchase, notify_ticket_purchase_confirmation
from app.services.PaystackServices import PaystackService
from app.core.config import settings

router = APIRouter(prefix="/public-events", tags=["public-events"])

graph_client = MicrosoftGraphClientPublic(
    tenant_id=settings.MICROSOFT_TENANT_ID,
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET
)


@router.get("/", response_model=List[EventResponse])
async def list_events(
    published_only: bool = True,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(aget_db)
):
    """Get list of events (public endpoint)"""
    query = select(PublicEvent).options(
        selectinload(PublicEvent.ticket_types)  # Eagerly load ticket_types
    )
    
    if published_only:
        query = query.where(PublicEvent.is_published == True)
    
    query = query.offset(skip).limit(limit).order_by(PublicEvent.event_date.desc())
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return events

@router.get("/{event_slug}", response_model=EventResponse)
async def get_event(
    event_slug: str,
    db: AsyncSession = Depends(aget_db)
):
    """Get event details by slug (public endpoint)"""
    result = await db.execute(
        select(PublicEvent)
        .options(selectinload(PublicEvent.ticket_types))  # Add this
        .where(PublicEvent.slug == event_slug)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.is_published:
        raise HTTPException(status_code=404, detail="Event not available")
    
    return event

@router.get("/{event_slug}/ticket-types", response_model=List[EventTicketTypeResponse])
async def get_event_ticket_types(
    event_slug: str,
    db: AsyncSession = Depends(aget_db)
):
    """Get available ticket types for an event, ordered by tier and price"""
    
    # Define tier order for sorting
    tier_order = {
        TicketTier.REGULAR: 1,
        TicketTier.VIP: 2,
        TicketTier.VVIP: 3
    }
    
    result = await db.execute(
        select(PublicEvent)
        .options(selectinload(PublicEvent.ticket_types))
        .where(PublicEvent.slug == event_slug)
    )
    event = result.scalar_one_or_none()
    
    if not event or not event.is_published:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Sort ticket types: first by tier, then by price
    sorted_tickets = sorted(
        event.ticket_types,
        key=lambda t: (tier_order.get(t.tier, 999), t.price)
    )
    
    return sorted_tickets


@router.post("/tickets/purchase")
async def purchase_ticket(
    purchase_data: TicketPurchaseRequest,
    db: AsyncSession = Depends(aget_db)
):
    """Purchase event ticket(s) - creates or uses existing EventUser"""
    
    # Get or create EventUser
    result = await db.execute(
        select(EventUser).where(EventUser.email == purchase_data.attendee_email)
    )
    event_user = result.scalar_one_or_none()
    
    if not event_user:
        # Create new event user
        event_user = EventUser(
            email=purchase_data.attendee_email,
            full_name=purchase_data.attendee_name,
            phone=purchase_data.attendee_phone
        )
        db.add(event_user)
        await db.flush()
    
    # Verify event exists and is published
    event = await db.get(PublicEvent, purchase_data.event_id)
    if not event or not event.is_published:
        raise HTTPException(status_code=404, detail="Event not found or not available")
    
    # Verify ticket type exists and is available
    ticket_type = await db.get(EventTicketType, purchase_data.ticket_type_id)
    if not ticket_type or ticket_type.event_id != event.id:
        raise HTTPException(status_code=404, detail="Ticket type not found")
    
    if not ticket_type.is_available:
        raise HTTPException(status_code=400, detail="This ticket type is no longer available")
    
    # Check availability
    if ticket_type.is_sold_out:
        raise HTTPException(status_code=400, detail="Tickets sold out")
    
    if ticket_type.quantity_available:
        if ticket_type.available_quantity < purchase_data.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Only {ticket_type.available_quantity} tickets remaining"
            )
    
    # Calculate total amount
    total_amount = ticket_type.price * purchase_data.quantity
    
    # Generate payment reference
    reference = f"TKT-{uuid4().hex[:10].upper()}"
    
    # Create pending ticket record(s)
    tickets = []
    for i in range(purchase_data.quantity):
        ticket = EventTicket(
            event_id=event.id,
            ticket_type_id=ticket_type.id,
            event_user_id=event_user.id,
            ticket_number=f"TEMP-{uuid4().hex[:8].upper()}",  # Temporary, will be updated on confirmation
            attendee_name=purchase_data.attendee_name,
            attendee_email=purchase_data.attendee_email,
            attendee_phone=purchase_data.attendee_phone,
            price_paid=ticket_type.price,
            payment_reference=reference,
            status=TicketStatus.PENDING
        )
        tickets.append(ticket)
        db.add(ticket)
    
    await db.flush()
    
    # Create payment record
    payment = Payment(
        event_user_id=event_user.id,
        amount=total_amount,
        purpose=PaymentPurpose.EVENT_TICKET,
        status=PaymentStatus.PENDING,
        transaction_reference=reference,
        payment_metadata={
            "event_id": event.id,
            "ticket_type_id": ticket_type.id,
            "quantity": purchase_data.quantity,
            "ticket_ids": [t.id for t in tickets]
        }
    )
    db.add(payment)
    await db.commit()
    
    # 🔑 Build verification URL with reference parameter
    verification_url = purchase_data.callback_url or f"{settings.FRONTEND_URL}/events/payment-callback"
    # Add reference as query parameter
    if "?" in verification_url:
        verification_url += f"&reference={reference}"
    else:
        verification_url += f"?reference={reference}"
    
    # Initialize Paystack payment
    try:
        paystack_data = PaymentInitRequest(
            amount=float(total_amount),
            email=event_user.email,
            callback_url=verification_url,  # For fallback
            redirect_url=verification_url,  # 🔑 NEW: Direct redirect to our verification page
            purpose=PaymentPurpose.EVENT_TICKET,
            reference=reference,
            send_email_notification=False,  # We handle emails ourselves
            payment_metadata={
                "event_name": event.title,
                "ticket_type": ticket_type.name,
                "quantity": purchase_data.quantity,
                "attendee_name": purchase_data.attendee_name
            }
        )
        
        # 🔍 LOGGING: Paystack payment initialization
        print("\n" + "="*80)
        print("💳 PAYSTACK TICKET PAYMENT INITIALIZATION")
        print("="*80)
        print(f"Amount to charge: {float(total_amount)} GHS")
        print(f"Customer Email: {event_user.email}")
        print(f"Payment Reference: {reference}")
        print(f"Redirect URL: {verification_url}")
        print(f"Event: {event.title}")
        print(f"Ticket Type: {ticket_type.name}")
        print(f"Quantity: {purchase_data.quantity}")
        print("="*80 + "\n")
        
        response = await PaystackService.initialize_payment(data=paystack_data)
        
        # 🔍 LOGGING: Success
        print("\n" + "="*80)
        print("✅ TICKET PURCHASE INITIATION SUCCESSFUL")
        print("="*80)
        print(f"Payment Reference: {reference}")
        print(f"Total Amount: {float(total_amount)} GHS")
        print(f"Payment URL: {response['data']['authorization_url']}")
        print(f"Number of Tickets: {len(tickets)}")
        print("="*80 + "\n")
        
        return {
            "payment_reference": reference,
            "payment_url": response["data"]["authorization_url"],
            "ticket_ids": [t.id for t in tickets],
            "total_amount": total_amount,
            "event_name": event.title,
            "ticket_type": ticket_type.name,
            "quantity": purchase_data.quantity
        }
        
    except Exception as e:
        # Rollback tickets and payment
        print(f"\n❌ PAYSTACK ERROR: {str(e)}\n")
        for ticket in tickets:
            await db.delete(ticket)
        await db.delete(payment)
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Payment initialization failed: {str(e)}")

@router.get("/tickets/verify")
async def verify_ticket_payment(
    reference: str,
    db: AsyncSession = Depends(aget_db)
):
    """Verify ticket payment and confirm tickets"""
    # Get payment record with relationships
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.event_user))
        .where(Payment.transaction_reference == reference)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status == PaymentStatus.COMPLETED:
        return {
            "message": "Payment already verified",
            "status": "success",
            "ticket_numbers": [t.ticket_number for t in payment.event_tickets]
        }
    
    # Verify with Paystack
    try:
        verification = await PaystackService.verify_transaction(reference)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update payment status
    payment.status = PaymentStatus.COMPLETED
    payment.payment_date = datetime.fromisoformat(
        verification["paid_at"].replace("Z", "+00:00")
    ).replace(tzinfo=None)
    
    # Get and confirm tickets
    ticket_ids = payment.payment_metadata.get("ticket_ids", [])
    result = await db.execute(
        select(EventTicket)
        .options(
            selectinload(EventTicket.event),
            selectinload(EventTicket.ticket_type)
        )
        .where(EventTicket.id.in_(ticket_ids))
    )
    tickets = result.scalars().all()
    
    if not tickets:
        raise HTTPException(status_code=404, detail="Tickets not found")
    
    ticket_numbers = []
    ticket_data_list = []
    event = tickets[0].event  # All tickets are for the same event
    
    for ticket in tickets:
        # Generate final ticket number
        ticket.ticket_number = ticket.generate_ticket_number()
        
        # Generate QR code with URL for verification page
        
        qr_result = generate_event_qr_code_with_logo(
            registration_data={
                "registration_id": ticket.ticket_number,
                "ticket_number": ticket.ticket_number,
                "event_id": event.id,
                "email": ticket.attendee_email,
                "name": ticket.attendee_name,
                "type": "event_ticket"
            },
            logo_path="app/static/images/yellow-logo.png",
            base_url=f'{settings.FRONTEND_URL}/events/{event.slug}/ticket-verify'
        )
        
        ticket.qr_code = f"data:image/png;base64,{qr_result['qr_code_base64']}"
        
        # Confirm ticket
        ticket.confirm_ticket()
        ticket_numbers.append(ticket.ticket_number)
        
        # Prepare ticket data for email
        ticket_data_list.append({
            'ticket_number': ticket.ticket_number,
            'ticket_type': ticket.ticket_type.name,
            'attendee_name': ticket.attendee_name,
            'attendee_email': ticket.attendee_email,
            'qr_code': ticket.qr_code,
            'price_paid': ticket.price_paid
        })
        
        db.add(ticket)
    
    # Update event user last purchase date
    if payment.event_user:
        payment.event_user.last_purchase_at = datetime.utcnow()
    
    db.add(payment)
    await db.commit()
    
    # Prepare email data
    email_data = {
        'tickets': ticket_data_list,
        'event': {
            'title': event.title,
            'event_date': event.event_date,
            'event_time': event.event_time,
            'venue_name': event.venue_name,
            'venue_address': event.venue_address
        },
        'payment_reference': reference,
        'payment_date': payment.payment_date,
        'attendee_email': tickets[0].attendee_email,
        'attendee_name': tickets[0].attendee_name
    }
    
    # Send confirmation email to customer
    try:
        
        customer_email_result = await notify_ticket_purchase_confirmation(
            email_data, 
            graph_client
        )
        
        if customer_email_result['status'] == 'failed':
            print(f"⚠️ Customer email failed: {customer_email_result.get('error')}")
        
        # Send notification to admin team
        admin_email_result = await notify_admin_new_ticket_purchase(
            ticket_data=email_data,
            graph_client=graph_client,
            admin_emails=ADMIN_EMAILS
        )
        
        if admin_email_result['status'] == 'failed':
            print(f"⚠️ Admin notification failed: {admin_email_result.get('error')}")
        
    except Exception as e:
        print(f"⚠️ Failed to send notification emails: {e}")
        traceback.print_exc()
        # Don't fail the entire request if email fails
    
    return {
        "message": "Tickets confirmed successfully",
        "status": "success",
        "ticket_numbers": ticket_numbers,
        "payment_reference": reference
    }


@router.get("/tickets/my-tickets", response_model=List[EventTicketResponse])
async def get_my_tickets(
    email: str = Query(..., description="Email address to look up tickets"),
    status: Optional[str] = None,
    db: AsyncSession = Depends(aget_db)
):
    """Get tickets by email address"""
    # Find event user
    result = await db.execute(
        select(EventUser).where(EventUser.email == email)
    )
    event_user = result.scalar_one_or_none()
    
    if not event_user:
        return []
    
    query = select(EventTicket).where(EventTicket.event_user_id == event_user.id)
    
    if status:
        query = query.where(EventTicket.status == status)
    
    query = query.order_by(EventTicket.purchased_at.desc())
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    return tickets

@router.get("/tickets/{ticket_number}", response_model=EventTicketResponse)
async def get_ticket_details(
    ticket_number: str,
    email: str = Query(..., description="Email address for verification"),
    db: AsyncSession = Depends(aget_db)
):
    """Get ticket details by ticket number and email"""
    result = await db.execute(
        select(EventTicket).where(
            and_(
                EventTicket.ticket_number == ticket_number,
                EventTicket.attendee_email == email
            )
        )
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket

# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin/events", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    request: Request,
    db: AsyncSession = Depends(aget_db)
):
    """Create new event (admin only)"""
    # TODO: Add admin authentication check
    
    event = PublicEvent(**event_data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return event

@router.put("/admin/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    request: Request,
    db: AsyncSession = Depends(aget_db)
):
    """Update event (admin only)"""
    # TODO: Add admin authentication check
    
    event = await db.get(PublicEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update only provided fields
    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return event

@router.post("/admin/events/{event_id}/ticket-types", response_model=EventTicketTypeResponse)
async def create_ticket_type(
    event_id: int,
    ticket_data: EventTicketTypeCreate,
    request: Request,
    db: AsyncSession = Depends(aget_db)
):
    """Create ticket type for event (admin only)"""
    # TODO: Add admin authentication check
    
    event = await db.get(PublicEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    ticket_type = EventTicketType(**ticket_data.model_dump())
    db.add(ticket_type)
    await db.commit()
    await db.refresh(ticket_type)
    
    return ticket_type

@router.post("/admin/tickets/check-in", response_model=TicketCheckInResponse)
async def check_in_ticket(
    check_in_data: TicketCheckInRequest,
    staff_email: str = Query(..., description="Staff email for check-in"),
    db: AsyncSession = Depends(aget_db)
):
    """Check in a ticket (admin/staff only)"""
    # Get or create staff event user
    result = await db.execute(
        select(EventUser).where(EventUser.email == staff_email)
    )
    staff_user = result.scalar_one_or_none()
    
    if not staff_user:
        raise HTTPException(status_code=401, detail="Staff user not found")
    
    # Get ticket
    result = await db.execute(
        select(EventTicket).where(
            EventTicket.ticket_number == check_in_data.ticket_number
        )
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return TicketCheckInResponse(
            success=False,
            message="Ticket not found"
        )
    
    if ticket.status != TicketStatus.CONFIRMED:
        return TicketCheckInResponse(
            success=False,
            message=f"Ticket status is {ticket.status}, cannot check in",
            ticket=ticket
        )
    
    if ticket.checked_in:
        return TicketCheckInResponse(
            success=False,
            message=f"Ticket already checked in at {ticket.checked_in_at}",
            ticket=ticket
        )
    
    # Check in the ticket
    ticket.checked_in = True
    ticket.checked_in_at = datetime.utcnow()
    ticket.checked_in_by = staff_user.id
    ticket.status = TicketStatus.USED
    
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    return TicketCheckInResponse(
        success=True,
        message="Ticket checked in successfully",
        ticket=ticket
    )

@router.get("/admin/events/{event_id}/statistics", response_model=EventStatistics)
async def get_event_statistics(
    event_id: int,
    request: Request,
    db: AsyncSession = Depends(aget_db)
):
    """Get event statistics (admin only)"""
    # TODO: Add admin authentication check
    
    event = await db.get(PublicEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get ticket statistics
    result = await db.execute(
        select(
            EventTicket.status,
            func.count(EventTicket.id).label('count'),
            func.sum(EventTicket.price_paid).label('revenue')
        )
        .where(EventTicket.event_id == event_id)
        .group_by(EventTicket.status)
    )
    stats = result.all()
    
    total_sold = sum(s.count for s in stats if s.status == TicketStatus.CONFIRMED)
    total_revenue = sum(s.revenue for s in stats if s.status == TicketStatus.CONFIRMED) or 0
    
    # Check-in statistics
    result = await db.execute(
        select(func.count(EventTicket.id))
        .where(
            and_(
                EventTicket.event_id == event_id,
                EventTicket.checked_in == True
            )
        )
    )
    check_in_count = result.scalar() or 0
    
    # Tickets by tier
    result = await db.execute(
        select(
            EventTicketType.name,
            func.count(EventTicket.id).label('count')
        )
        .join(EventTicket)
        .where(
            and_(
                EventTicket.event_id == event_id,
                EventTicket.status == TicketStatus.CONFIRMED
            )
        )
        .group_by(EventTicketType.name)
    )
    tickets_by_tier = {row.name: row.count for row in result.all()}
    
    return EventStatistics(
        total_tickets_sold=total_sold,
        total_revenue=total_revenue,
        tickets_by_tier=tickets_by_tier,
        check_in_count=check_in_count,
        check_in_percentage=(check_in_count / total_sold * 100) if total_sold > 0 else 0
    )


@router.post("/tickets/verify-qr")
async def verify_ticket_qr_code(
    ticket_number: str = Form(...),
    event_id: int = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Verify a ticket QR code and automatically check in the attendee.
    Requires authenticated staff user.
    
    Form Parameters:
        ticket_number: The ticket number to verify
        event_id: The event ID
        email: Attendee's email
        name: Attendee's name
        type: Should be "event_ticket"
    """
    try:
        # Validate the type
        if type != "event_ticket":
            raise HTTPException(
                status_code=400,
                detail="This QR code is not for an event ticket"
            )
        
        # Get or create EventUser for the current authenticated user
        result = await db.execute(
            select(EventUser).where(EventUser.email == current_user.email)
        )
        event_user = result.scalar_one_or_none()
        
        if not event_user:
            # Create EventUser record for this staff member
            event_user = EventUser(
                email=current_user.email,
                full_name=f"{current_user.first_name} {current_user.last_name}",
                phone=current_user.phone
            )
            db.add(event_user)
            await db.flush()  # Get the ID without committing
        
        # Get ticket from database with relationships
        result = await db.execute(
            select(EventTicket)
            .options(
                selectinload(EventTicket.event),
                selectinload(EventTicket.ticket_type)
            )
            .where(EventTicket.ticket_number == ticket_number)
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )
        
        # Verify email matches
        if ticket.attendee_email.lower() != email.lower():
            raise HTTPException(
                status_code=400,
                detail="Ticket details do not match"
            )
        
        # Verify event ID matches
        if ticket.event_id != event_id:
            raise HTTPException(
                status_code=400,
                detail="Ticket is not for this event"
            )
        
        # Check if cancelled
        if ticket.status == TicketStatus.CANCELLED:
            raise HTTPException(
                status_code=400,
                detail="This ticket has been cancelled"
            )
        
        # Check if ticket is confirmed (paid)
        if ticket.status != TicketStatus.CONFIRMED and ticket.status != TicketStatus.USED:
            raise HTTPException(
                status_code=400,
                detail="This ticket has not been confirmed. Payment may still be pending."
            )
        
        # Check if already checked in
        already_checked_in = ticket.checked_in
        
        # Perform check-in if not already checked in
        if not already_checked_in:
            ticket.checked_in = True
            ticket.checked_in_at = datetime.utcnow()
            ticket.checked_in_by = event_user.id  # Use EventUser's integer ID
            ticket.status = TicketStatus.USED
            
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)
        
        # Return ticket info with check-in status
        return {
            "valid": True,
            "ticket_number": ticket.ticket_number,
            "attendee_name": ticket.attendee_name,
            "attendee_email": ticket.attendee_email,
            "attendee_phone": ticket.attendee_phone,
            "ticket_type": ticket.ticket_type.name,
            "price_paid": float(ticket.price_paid),
            "status": ticket.status.value,
            "already_checked_in": already_checked_in,
            "checked_in_at": ticket.checked_in_at.isoformat() if ticket.checked_in_at else None,
            "checked_in_by_name": f"{current_user.first_name} {current_user.last_name}" if not already_checked_in else None,
            "purchased_at": ticket.purchased_at.isoformat() if ticket.purchased_at else None,
            "confirmed_at": ticket.confirmed_at.isoformat() if ticket.confirmed_at else None,
            "event_details": {
                "id": ticket.event.id,
                "title": ticket.event.title,
                "slug": ticket.event.slug,
                "event_date": ticket.event.event_date.isoformat(),
                "event_time": ticket.event.event_time,
                "venue_name": ticket.event.venue_name,
                "venue_address": ticket.event.venue_address
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error verifying ticket QR code: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify ticket QR code")


@router.post("/tickets/check-in/{ticket_number}")
async def check_in_ticket(
    ticket_number: str,
    staff_email: str = Query(..., description="Staff email performing check-in"),
    db: AsyncSession = Depends(aget_db)
):
    """
    Check in a ticket holder using their ticket number (from QR code).
    Marks the ticket as used.
    """
    try:
        # Get or verify staff user
        result = await db.execute(
            select(EventUser).where(EventUser.email == staff_email)
        )
        staff_user = result.scalar_one_or_none()
        
        if not staff_user:
            raise HTTPException(
                status_code=401,
                detail="Staff user not found. Please register as staff first."
            )
        
        # Get ticket
        result = await db.execute(
            select(EventTicket)
            .options(
                selectinload(EventTicket.event),
                selectinload(EventTicket.ticket_type)
            )
            .where(EventTicket.ticket_number == ticket_number)
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )
        
        # Check if already checked in
        if ticket.checked_in:
            return {
                "message": "Ticket already checked in",
                "ticket_number": ticket_number,
                "checked_in_at": ticket.checked_in_at.isoformat(),
                "already_checked_in": True,
                "attendee_name": ticket.attendee_name,
                "attendee_email": ticket.attendee_email,
                "ticket_type": ticket.ticket_type.name
            }
        
        # Verify ticket is confirmed
        if ticket.status != TicketStatus.CONFIRMED:
            raise HTTPException(
                status_code=400,
                detail=f"Ticket cannot be checked in. Current status: {ticket.status.value}"
            )
        
        # Check in the ticket
        ticket.checked_in = True
        ticket.checked_in_at = datetime.utcnow()
        ticket.checked_in_by = staff_user.id
        ticket.status = TicketStatus.USED
        
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        
        return {
            "message": "Check-in successful",
            "ticket_number": ticket_number,
            "attendee_name": ticket.attendee_name,
            "attendee_email": ticket.attendee_email,
            "attendee_phone": ticket.attendee_phone,
            "ticket_type": ticket.ticket_type.name,
            "checked_in_at": ticket.checked_in_at.isoformat(),
            "already_checked_in": False,
            "event_details": {
                "title": ticket.event.title,
                "venue_name": ticket.event.venue_name
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error during check-in: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check in ticket holder"
        )