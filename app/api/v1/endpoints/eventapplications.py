"""API endpoints for AXI Event Application Forms with Email Notifications."""

import json
import uuid
import traceback
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from sqlalchemy.orm import selectinload
from app.constants.constants import ADMIN_EMAILS, AgeRange, Availability, EventStatus, JobStatus, OrganizationType, TicketStatus
from app.core.database import aget_db

from app.core.security import get_current_user
from app.models.axilaunchattendance import AxiLaunchAttendance
from app.models.becomingthefirstattendees import BecomingTheFirstAttendance
from app.models.contactmessage import ContactMessage
from app.models.job import Job
from app.models.jobwaitlist import JobWaitlist
from app.models.partnershipapplication import PartnershipApplication
from app.models.publicevents import EventTicket, PublicEvent
from app.models.speakerapplication import SpeakerApplication
from app.models.sponsorshipapplication import SponsorshipApplication
from app.models.user import User
from app.models.volunteeapplication import VolunteerApplication
from app.schemas.axilaunchSchema import AxiLaunchRequest, AxiLaunchResponse
from app.schemas.becomingthefirstSchema import BecomingTheFirstRequest, BecomingTheFirstResponse
from app.schemas.contactmessageSchema import ContactMessageRequest, ContactMessageResponse
from app.schemas.jobwaitlistSchema import JobWaitlistRequest, JobWaitlistResponse
from app.services.EventApplicationConfirmationEmail import notify_admin_new_axi_launch_registration, notify_admin_new_becoming_first_registration, notify_admin_new_contact_message, notify_admin_new_partnership_application, notify_admin_new_speaker_application, notify_admin_new_sponsorship_application, notify_admin_new_volunteer_application, notify_admin_new_waitlist_signup, notify_axi_launch_registration_confirmation, notify_becoming_first_registration_confirmation, notify_contact_message_received, notify_job_waitlist_confirmation, notify_partnership_application_received, notify_speaker_application_received, notify_sponsorship_application_received, notify_volunteer_application_received, notify_waitlisters_new_job
from app.services.EventQRCodeGenerator import generate_axi_launch_qr_code
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.services.TicketGenerator import generate_axi_launch_ticket_pdf
from app.utils.uploads.val_upload_avatar import validate_and_upload_avatar
from app.core.config import settings  # Assuming you have settings for MS Graph credentials

router = APIRouter(
    prefix="/event-applications",
    tags=["event-applications"]
)

# Configuration for duplicate submission window (in hours)
DUPLICATE_SUBMISSION_WINDOW = 24


def normalize_email(email: str) -> str:
    """Normalize email by converting to lowercase and stripping whitespace."""
    return email.strip().lower()


async def check_duplicate_submission(
    db: AsyncSession,
    model_class,
    email: str,
    organization_name: Optional[str] = None,
    window_hours: int = DUPLICATE_SUBMISSION_WINDOW
) -> bool:
    """
    Check if a duplicate submission exists within the specified time window.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class to check
        email: Email to check for duplicates
        organization_name: Organization name for partnership/sponsorship checks
        window_hours: Time window in hours to check for duplicates
    
    Returns:
        True if duplicate exists, False otherwise
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
    normalized_email = normalize_email(email)
    
    # Build query conditions
    conditions = [
        model_class.email == normalized_email,
        model_class.submitted_at >= cutoff_time
    ]
    
    # For partnership and sponsorship, also check organization name
    if organization_name and hasattr(model_class, 'organization_name'):
        conditions.append(
            model_class.organization_name == organization_name
        )
    
    query = select(model_class).where(and_(*conditions))
    
    result = await db.execute(query)
    existing_application = result.scalar_one_or_none()
    
    return existing_application is not None

async def check_duplicate_message(
    db: AsyncSession,
    email: str,
    subject: str,
    window_hours: int = DUPLICATE_SUBMISSION_WINDOW
) -> bool:
    """
    Check if a duplicate message exists within the specified time window.
    
    Args:
        db: Database session
        email: Email to check for duplicates
        subject: Subject to check for duplicates
        window_hours: Time window in hours to check for duplicates
    
    Returns:
        True if duplicate exists, False otherwise
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
    normalized_email = normalize_email(email)
    
    query = select(ContactMessage).where(
        and_(
            ContactMessage.email == normalized_email,
            ContactMessage.subject == subject,
            ContactMessage.submitted_at >= cutoff_time
        )
    )
    
    result = await db.execute(query)
    existing_message = result.scalar_one_or_none()
    
    return existing_message is not None


def get_graph_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="axi@ideationaxis.com"
    )

def get_graph_root_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="info@ideationaxis.com"
    )

@router.get("/upcoming-events")
async def get_upcoming_events(
    db: AsyncSession = Depends(aget_db)
):
    """Get published future events for application forms."""
    try:
        now = datetime.utcnow()
        
        query = select(PublicEvent).where(
            and_(
                PublicEvent.is_published == True,
                PublicEvent.event_date > now
            )
        ).order_by(PublicEvent.event_date.asc())
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        event_list = [
            {
                "id": event.id,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "slug": event.slug
            }
            for event in events
        ]
        
        return {"events": event_list}
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching upcoming events: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch upcoming events"
        )


@router.post("/public-events/create-event")
async def create_event(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    event_date: str = Form(...),
    event_time: str = Form(...),
    event_end_date: Optional[str] = Form(None),
    venue_name: str = Form(...),
    venue_address: str = Form(...),
    city: str = Form(...),
    country: str = Form(...),
    max_attendees: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    banner_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Create a new public event.
    Requires authenticated user with proper authorization.
    """
    try:
        # Check authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah Gyimah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to create events"
            )
        
        # Validate required fields
        if not title or len(title) < 5:
            raise HTTPException(
                status_code=400,
                detail="Title must be at least 5 characters"
            )
        
        if not description or len(description) < 50:
            raise HTTPException(
                status_code=400,
                detail="Description must be at least 50 characters"
            )
        
        # Parse event_date
        try:
            event_date_obj = datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid event date format. Use YYYY-MM-DD"
            )
        
        # Parse event_end_date if provided
        event_end_date_obj = None
        if event_end_date:
            try:
                event_end_date_obj = datetime.strptime(event_end_date, "%Y-%m-%d")
                if event_end_date_obj < event_date_obj:
                    raise HTTPException(
                        status_code=400,
                        detail="End date cannot be before start date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end date format. Use YYYY-MM-DD"
                )
        
        # Generate slug from title
        slug = title.lower()
        slug = slug.replace(" ", "-")
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        slug = '-'.join(filter(None, slug.split('-')))
        
        # Check if slug already exists
        existing_event = await db.execute(
            select(PublicEvent).where(PublicEvent.slug == slug)
        )
        if existing_event.scalar_one_or_none():
            # Add timestamp to make it unique
            slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
        
        # Parse max_attendees
        max_attendees_int = None
        if max_attendees and max_attendees.strip():
            try:
                max_attendees_int = int(max_attendees)
                if max_attendees_int <= 0:
                    raise ValueError("Max attendees must be positive")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Max attendees must be a valid positive number"
                )
        
        # Create event
        new_event = PublicEvent(
            slug=slug,
            title=title.strip(),
            description=description.strip(),
            category=category.strip(),
            event_date=event_date_obj,
            event_time=event_time.strip(),
            event_end_date=event_end_date_obj,
            venue_name=venue_name.strip(),
            venue_address=venue_address.strip(),
            city=city.strip(),
            country=country.strip(),
            max_attendees=max_attendees_int,
            image_url=image_url,
            banner_url=banner_url,
            status=EventStatus.PUBLISHED,
            is_published=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_event)
        
        try:
            await db.commit()
            await db.refresh(new_event)
        except Exception as e:
            await db.rollback()
            error_traceback = traceback.format_exc()
            print(f"Database commit error: {error_traceback}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create event: {str(e)}"
            )
        
        return {
            "message": "Event created successfully",
            "id": new_event.id,
            "slug": new_event.slug,
            "title": new_event.title,
            "event_date": new_event.event_date.isoformat(),
            "status": new_event.status.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error creating event: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the event"
        )

@router.post("/partnership")
async def submit_partnership_application(
    organization_name: str = Form(...),
    organization_type: str = Form(...),
    contact_person_name: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    event_id: Optional[int] = Form(None),
    linkedin_website: Optional[str] = Form(None),
    partnership_types: str = Form(...),
    other_reason: Optional[str] = Form(None),
    value_to_bring: Optional[str] = Form(None),
    value_to_receive: Optional[str] = Form(None),
    how_heard_about_axi: Optional[str] = Form(None),
    authorized_contact: bool = Form(False),
    proposal_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(aget_db)
):
    """Submit partnership application."""
    try:
        print(f"DEBUG: Starting partnership application for {organization_name}")
        
        # Normalize email
        normalized_email = normalize_email(email)
        print(f"DEBUG: Normalized email: {normalized_email}")
        
        # Check for duplicate submission with better error handling
        try:
            print(f"DEBUG: Checking for duplicates...")
            is_duplicate = await check_duplicate_submission(
                db, 
                PartnershipApplication, 
                normalized_email,
                organization_name
            )
            print(f"DEBUG: Duplicate check result: {is_duplicate}")
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error in duplicate check: {error_traceback}")
            # If duplicate check fails, proceed with submission rather than blocking it
            is_duplicate = False
        
        if is_duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"A partnership application for '{organization_name}' with this email was already submitted within the last {DUPLICATE_SUBMISSION_WINDOW} hours."
            )
        
        # Validate organization_type
        try:
            print(f"DEBUG: Validating organization_type: {organization_type}")
            org_type = OrganizationType(organization_type)
            print(f"DEBUG: Organization type validated: {org_type}")
        except ValueError:
            valid_types = [e.value for e in OrganizationType]
            print(f"DEBUG: Invalid organization type: {organization_type}. Valid: {valid_types}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid organization type: '{organization_type}'. Valid values are: {valid_types}"
            )
        
        # Validate partnership_types JSON
        try:
            print(f"DEBUG: Validating partnership_types JSON: {partnership_types}")
            partnership_types_list = json.loads(partnership_types)
            if not isinstance(partnership_types_list, list):
                raise ValueError("Partnership types must be a list")
            partnership_types_json = json.dumps(partnership_types_list)
            print(f"DEBUG: Partnership types validated: {partnership_types_json}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"DEBUG: Invalid partnership types format: {str(e)}. Input was: {partnership_types}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid partnership types format: {str(e)}. Expected a JSON array."
            )
        
        print(f"DEBUG: Proposal URL: {proposal_url if proposal_url else 'None'}")
        
        # Create application
        print(f"DEBUG: Creating application object...")
        application = PartnershipApplication(
            application_id=str(uuid.uuid4()),
            organization_name=organization_name,
            organization_type=org_type,
            contact_person_name=contact_person_name,
            phone_number=phone_number,
            email=normalized_email,
            event_id=event_id,
            linkedin_website=linkedin_website,
            partnership_types=partnership_types_json,
            other_reason=other_reason,
            value_to_bring=value_to_bring,
            value_to_receive=value_to_receive,
            referrer=how_heard_about_axi,
            proposal_url=proposal_url,  # Use the already uploaded URL
            authorized_contact=authorized_contact,
            submitted_at=datetime.utcnow()
        )
        print(f"DEBUG: Application object created")
        
        try:
            print(f"DEBUG: Adding application to database...")
            db.add(application)
            await db.commit()
            await db.refresh(application)
            print(f"DEBUG: Database commit successful")
        except Exception as e:
            await db.rollback()
            # Log the actual database error
            db_error_traceback = traceback.format_exc()
            print(f"Database commit error: {db_error_traceback}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to submit application to database: {str(e)}"
            )
        
        # Send confirmation email
        try:
            graph_client = get_graph_client()
            application_data = {
                'email': normalized_email,
                'contact_person_name': contact_person_name,
                'organization_name': organization_name,
                'application_id': application.application_id,
                'organization_type': organization_type,
                'event_id': event_id,
                'submitted_at': application.submitted_at
            }
            
            email_result = await notify_partnership_application_received(
                application_data=application_data,
                graph_client=graph_client
            )
            
            if email_result['status'] == 'failed':
                print(f"⚠️ Email sending failed but application was saved: {email_result.get('error')}")

            admin_result = await notify_admin_new_partnership_application(
                application_data={
                    **application_data,
                    'phone_number': phone_number,
                    'linkedin_website': linkedin_website,
                    'partnership_types': partnership_types_json,
                    'value_to_bring': value_to_bring,
                    'value_to_receive': value_to_receive,
                    'referrer': how_heard_about_axi,
                },
                graph_client=graph_client
            )
            
            if admin_result['status'] == 'failed':
                print(f"⚠️ Admin notification failed: {admin_result.get('error')}")

        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send confirmation email: {str(email_error)}")
            traceback.print_exc()
        
        return {
            "message": "Partnership application submitted successfully!",
            "application_id": application.application_id
        }
    
    except HTTPException as he:
        print(f"DEBUG: HTTPException raised: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        # Log the full traceback for unexpected errors
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in partnership application: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your partnership application. Please try again later."
        )


@router.post("/speaker")
async def submit_speaker_application(
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    event_id: int = Form(...),
    linkedin_website: Optional[str] = Form(None),
    role_organization: str = Form(...),
    country: str = Form(...),
    proposal_topic: str = Form(...),
    speaking_formats: str = Form(...),  # JSON string
    why_speak: str = Form(...),
    short_bio: str = Form(...),
    how_heard_about_axi: Optional[str] = Form(None),
    previous_engagements: Optional[str] = Form(None),
    authorized_contact: bool = Form(False),
    headshot: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(aget_db)
):
    """Submit speaker application."""
    try:
        # Normalize email
        normalized_email = normalize_email(email)
        
        # Check for duplicate submission
        if await check_duplicate_submission(db, SpeakerApplication, normalized_email):
            raise HTTPException(
                status_code=409,
                detail=f"A speaker application with this email was already submitted within the last {DUPLICATE_SUBMISSION_WINDOW} hours."
            )
        
        # Validate speaking_formats is valid JSON
        try:
            formats_list = json.loads(speaking_formats)
            if not isinstance(formats_list, list):
                raise ValueError("Speaking formats must be a list")
            # Convert back to JSON string for storage
            speaking_formats_json = json.dumps(formats_list)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid speaking formats format: {str(e)}")
        
        headshot_url = None
        if headshot:
            # Upload headshot to S3
            headshot_url = await validate_and_upload_avatar(
                headshot, 
                f"speaker_{full_name.replace(' ', '_')}"
            )
        
        application = SpeakerApplication(
            application_id=str(uuid.uuid4()),
            full_name=full_name,
            email=normalized_email,
            phone_number=phone_number,
            event_id=event_id,
            linkedin_website=linkedin_website,
            role_organization=role_organization,
            country=country,
            proposal_topic=proposal_topic,
            speaking_formats=speaking_formats_json,
            why_speak=why_speak,
            short_bio=short_bio,
            how_heard_about_axi=how_heard_about_axi,
            previous_engagements=previous_engagements,
            headshot_url=headshot_url,
            authorized_contact=authorized_contact,
            submitted_at=datetime.utcnow()
        )
        
        db.add(application)
        
        try:
            await db.commit()
            await db.refresh(application)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to submit application: {str(e)}")
        
        # Send confirmation email
        try:
            graph_client = get_graph_client()
            application_data = {
                'email': normalized_email,
                'full_name': full_name,
                'application_id': application.application_id,
                'proposal_topic': proposal_topic,
                'role_organization': role_organization,
                'country': country,
                'event_id': event_id,
                'submitted_at': application.submitted_at
            }
            
            email_result = await notify_speaker_application_received(
                application_data=application_data,
                graph_client=graph_client
            )
            
            if email_result['status'] == 'failed':
                print(f"⚠️ Email sending failed but application was saved: {email_result.get('error')}")

            admin_result = await notify_admin_new_speaker_application(
                application_data={
                    **application_data,
                    'phone_number': phone_number,
                    'speaking_formats': speaking_formats_json,
                    'why_speak': why_speak,
                    'short_bio': short_bio,
                    'previous_engagements': previous_engagements,
                },
                graph_client=graph_client
            )
            
            if admin_result['status'] == 'failed':
                print(f"⚠️ Admin notification failed: {admin_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send confirmation email: {str(email_error)}")
            traceback.print_exc()
        
        return {
            "message": "Speaker application submitted successfully!",
            "application_id": application.application_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in speaker application: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your speaker application. Please try again later."
        )


@router.post("/sponsorship")
async def submit_sponsorship_application(
    organization_name: str = Form(...),
    industry: str = Form(...),
    contact_person_name: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    event_id: int = Form(...),
    linkedin_website: Optional[str] = Form(None),
    sponsorship_tiers: str = Form(...),  # JSON string
    sponsorship_goals: str = Form(...),
    how_heard_about_axi: str = Form(...),
    booth_interest: Optional[bool] = Form(None),
    authorized_contact: bool = Form(False),
    headshot: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(aget_db)
):
    """Submit sponsorship application."""
    try:
        # Normalize email
        normalized_email = normalize_email(email)
        
        # Check for duplicate submission (email + organization combination)
        if await check_duplicate_submission(
            db, 
            SponsorshipApplication, 
            normalized_email,
            organization_name
        ):
            raise HTTPException(
                status_code=409,
                detail=f"A sponsorship application for '{organization_name}' with this email was already submitted within the last {DUPLICATE_SUBMISSION_WINDOW} hours."
            )
        
        # Validate sponsorship_tiers is valid JSON
        try:
            tiers_list = json.loads(sponsorship_tiers)
            if not isinstance(tiers_list, list):
                raise ValueError("Sponsorship tiers must be a list")
            # Convert back to JSON string for storage
            sponsorship_tiers_json = json.dumps(tiers_list)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid sponsorship tiers format: {str(e)}")
        
        headshot_url = None
        if headshot:
            # Upload headshot to S3
            headshot_url = await validate_and_upload_avatar(
                headshot, 
                f"sponsor_{organization_name.replace(' ', '_')}"
            )
        
        application = SponsorshipApplication(
            application_id=str(uuid.uuid4()),
            organization_name=organization_name,
            industry=industry,
            contact_person_name=contact_person_name,
            phone_number=phone_number,
            email=normalized_email,
            event_id=event_id,
            linkedin_website=linkedin_website,
            sponsorship_tiers=sponsorship_tiers_json,
            sponsorship_goals=sponsorship_goals,
            how_heard_about_axi=how_heard_about_axi,
            headshot_url=headshot_url,
            booth_interest=booth_interest,
            authorized_contact=authorized_contact,
            submitted_at=datetime.utcnow()
        )
        
        db.add(application)
        
        try:
            await db.commit()
            await db.refresh(application)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to submit application: {str(e)}")
        
        # Send confirmation email
        try:
            graph_client = get_graph_client()
            application_data = {
                'email': normalized_email,
                'contact_person_name': contact_person_name,
                'organization_name': organization_name,
                'application_id': application.application_id,
                'industry': industry,
                'sponsorship_tiers': sponsorship_tiers_json,
                'booth_interest': booth_interest,
                'event_id': event_id,
                'submitted_at': application.submitted_at
            }
            
            email_result = await notify_sponsorship_application_received(
                application_data=application_data,
                graph_client=graph_client
            )
            
            if email_result['status'] == 'failed':
                print(f"⚠️ Email sending failed but application was saved: {email_result.get('error')}")

            admin_result = await notify_admin_new_sponsorship_application(
                application_data={
                    **application_data,
                    'phone_number': phone_number,
                    'linkedin_website': linkedin_website,
                    'sponsorship_goals': sponsorship_goals,
                    'how_heard_about_axi': how_heard_about_axi,
                },
                graph_client=graph_client
            )
            
            if admin_result['status'] == 'failed':
                print(f"⚠️ Admin notification failed: {admin_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send confirmation email: {str(email_error)}")
            traceback.print_exc()
        
        return {
            "message": "Sponsorship application submitted successfully!",
            "application_id": application.application_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in sponsorship application: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your sponsorship application. Please try again later."
        )


@router.post("/volunteer")
async def submit_volunteer_application(
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    event_id: int = Form(...),
    current_role: str = Form(...),
    age_range: str = Form(...),
    why_volunteer: str = Form(...),
    skills: str = Form(...),
    volunteer_roles: str = Form(...),  # JSON string
    how_heard_about_axi: Optional[str] = Form(None),
    ambassador_interest: Optional[str] = Form(None),
    availability: str = Form(...),
    authorized_contact: bool = Form(False),
    db: AsyncSession = Depends(aget_db)
):
    """Submit volunteer application."""
    try:
        # Normalize email
        normalized_email = normalize_email(email)
        
        # Check for duplicate submission
        if await check_duplicate_submission(db, VolunteerApplication, normalized_email):
            raise HTTPException(
                status_code=409,
                detail=f"A volunteer application with this email was already submitted within the last {DUPLICATE_SUBMISSION_WINDOW} hours."
            )
        
        try:
            age_range_enum = AgeRange(age_range)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid age range")
        
        try:
            availability_enum = Availability(availability)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid availability option")
        
        # Validate volunteer_roles is valid JSON
        try:
            roles_list = json.loads(volunteer_roles)
            if not isinstance(roles_list, list):
                raise ValueError("Volunteer roles must be a list")
            # Convert back to JSON string for storage
            volunteer_roles_json = json.dumps(roles_list)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid volunteer roles format: {str(e)}")
        
        application = VolunteerApplication(
            application_id=str(uuid.uuid4()),
            full_name=full_name,
            email=normalized_email,
            phone_number=phone_number,
            event_id=event_id,
            current_role=current_role,
            age_range=age_range_enum,
            why_volunteer=why_volunteer,
            skills=skills,
            volunteer_roles=volunteer_roles_json,
            how_heard_about_axi=how_heard_about_axi,
            ambassador_interest=ambassador_interest,
            availability=availability_enum,
            authorized_contact=authorized_contact,
            submitted_at=datetime.utcnow()
        )
        
        db.add(application)
        
        try:
            await db.commit()
            await db.refresh(application)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to submit application: {str(e)}")
        
        # Send confirmation email
        try:
            graph_client = get_graph_client()
            application_data = {
                'email': normalized_email,
                'full_name': full_name,
                'application_id': application.application_id,
                'current_role': current_role,
                'volunteer_roles': volunteer_roles_json,
                'skills': skills,
                'availability': availability,
                'ambassador_interest': ambassador_interest or 'Not specified',
                'event_id': event_id,
                'submitted_at': application.submitted_at
            }
            
            email_result = await notify_volunteer_application_received(
                application_data=application_data,
                graph_client=graph_client
            )
            
            if email_result['status'] == 'failed':
                print(f"⚠️ Email sending failed but application was saved: {email_result.get('error')}")

            admin_result = await notify_admin_new_volunteer_application(
                application_data={
                    **application_data,
                    'phone_number': phone_number,
                    'age_range': age_range,
                    'why_volunteer': why_volunteer,
                },
                graph_client=graph_client
            )
            
            if admin_result['status'] == 'failed':
                print(f"⚠️ Admin notification failed: {admin_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send confirmation email: {str(email_error)}")
            traceback.print_exc()
        
        return {
            "message": "Volunteer application submitted successfully!",
            "application_id": application.application_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in volunteer application: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your volunteer application. Please try again later."
        )
    
@router.post("/message", response_model=ContactMessageResponse)
async def submit_contact_message(
    request: ContactMessageRequest,
    db: AsyncSession = Depends(aget_db)
):
    """Submit a contact form message."""
    try:
        # Normalize email
        normalized_email = normalize_email(request.email)
        
        # Check for duplicate submission
        try:
            is_duplicate = await check_duplicate_message(
                db,
                normalized_email,
                request.subject
            )
        except Exception as e:
            print(f"Error in duplicate check: {traceback.format_exc()}")
            is_duplicate = False
        
        if is_duplicate:
            raise HTTPException(
                status_code=429,
                detail=f"A message with this subject was already submitted within the last hour. Please wait before submitting again."
            )
        
        # Validate message length
        if len(request.message) < 10:
            raise HTTPException(
                status_code=400,
                detail="Message must be at least 10 characters long."
            )
        
        if len(request.message) > 5000:
            raise HTTPException(
                status_code=400,
                detail="Message must not exceed 5000 characters."
            )
        
        # Create contact message
        contact_message = ContactMessage(
            message_id=str(uuid.uuid4()),
            full_name=request.full_name.strip(),
            email=normalized_email,
            phone_number=request.phone_number.strip() if request.phone_number else None,
            subject=request.subject.strip(),
            message=request.message.strip(),
            authorized_contact=request.authorized_contact,
            submitted_at=datetime.utcnow()
        )
        
        db.add(contact_message)
        
        try:
            await db.commit()
            await db.refresh(contact_message)
        except Exception as e:
            await db.rollback()
            print(f"Database commit error: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save your message. Please try again later."
            )
        
        # Send confirmation emails
        try:
            graph_client = get_graph_root_client()
            message_data = {
                'email': normalized_email,
                'full_name': request.full_name,
                'message_id': contact_message.message_id,
                'phone_number': request.phone_number,
                'subject': request.subject,
                'message': request.message,
                'submitted_at': contact_message.submitted_at
            }
            
            # Send confirmation to user
            user_email_result = await notify_contact_message_received(
                message_data=message_data,
                graph_client=graph_client
            )
            
            if user_email_result['status'] == 'failed':
                print(f"⚠️ User confirmation email failed: {user_email_result.get('error')}")
            
            # Notify admin team
            admin_email_result = await notify_admin_new_contact_message(
                message_data=message_data,
                graph_client=graph_client,
                admin_emails=ADMIN_EMAILS
            )
            
            if admin_email_result['status'] == 'failed':
                print(f"⚠️ Admin notification email failed: {admin_email_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send emails: {str(email_error)}")
            traceback.print_exc()
        
        return ContactMessageResponse(
            message="Your message has been sent successfully! We'll get back to you soon.",
            message_id=contact_message.message_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in contact message: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while sending your message. Please try again later."
        )


@router.get("/messages")
async def get_contact_messages(
    skip: int = 0,
    limit: int = 50,
    is_read: Optional[bool] = None,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all contact messages (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(ContactMessage).order_by(ContactMessage.submitted_at.desc())
        
        if is_read is not None:
            query = query.where(ContactMessage.is_read == is_read)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        return {
            "messages": [
                {
                    "message_id": msg.message_id,
                    "full_name": msg.full_name,
                    "email": msg.email,
                    "phone_number": msg.phone_number,
                    "subject": msg.subject,
                    "message": msg.message,
                    "is_read": msg.is_read,
                    "is_replied": msg.is_replied,
                    "submitted_at": msg.submitted_at.isoformat()
                }
                for msg in messages
            ],
            "total": len(messages),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching contact messages: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch contact messages."
        )


@router.patch("/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Mark a contact message as read (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(ContactMessage).where(ContactMessage.message_id == message_id)
        result = await db.execute(query)
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message.is_read = True
        await db.commit()
        
        return {"message": "Message marked as read", "message_id": message_id}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update message")


@router.patch("/messages/{message_id}/replied")
async def mark_message_as_replied(
    message_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Mark a contact message as replied (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(ContactMessage).where(ContactMessage.message_id == message_id)
        result = await db.execute(query)
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message.is_replied = True
        message.is_read = True  # Also mark as read
        await db.commit()
        
        return {"message": "Message marked as replied", "message_id": message_id}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update message")
    
@router.post("/job-waitlist", response_model=JobWaitlistResponse)
async def submit_job_waitlist(
    request: JobWaitlistRequest,
    db: AsyncSession = Depends(aget_db)
):
    """Submit job waitlist registration."""
    try:
        # Normalize email
        normalized_email = normalize_email(request.email)
        
        # Check for duplicate submission within 30 days
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        
        query = select(JobWaitlist).where(
            and_(
                JobWaitlist.email == normalized_email,
                JobWaitlist.submitted_at >= cutoff_time,
                JobWaitlist.is_active == True
            )
        )
        
        result = await db.execute(query)
        existing_entry = result.scalar_one_or_none()
        
        if existing_entry:
            raise HTTPException(
                status_code=409,
                detail="You're already on the waitlist! We'll notify you when new roles open up."
            )
        
        # Validate required fields
        if not request.full_name.strip():
            raise HTTPException(status_code=400, detail="Full name is required")
        
        if not request.preferred_role.strip():
            raise HTTPException(status_code=400, detail="Preferred role is required")
        
        if len(request.phone_number) < 10:
            raise HTTPException(status_code=400, detail="Valid phone number is required")
        
        # Create waitlist entry
        waitlist_entry = JobWaitlist(
            waitlist_id=str(uuid.uuid4()),
            full_name=request.full_name.strip(),
            email=normalized_email,
            phone_number=request.phone_number.strip(),
            linkedin_url=request.linkedin_url.strip() if request.linkedin_url else None,
            preferred_role=request.preferred_role.strip(),
            submitted_at=datetime.utcnow(),
            notified=False,
            is_active=True
        )
        
        db.add(waitlist_entry)
        
        try:
            await db.commit()
            await db.refresh(waitlist_entry)
        except Exception as e:
            await db.rollback()
            print(f"Database commit error: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save your waitlist registration. Please try again later."
            )
        
        # Send confirmation emails
        try:
            graph_client = get_graph_root_client()
            waitlist_data = {
                'email': normalized_email,
                'full_name': request.full_name,
                'waitlist_id': waitlist_entry.waitlist_id,
                'phone_number': request.phone_number,
                'linkedin_url': request.linkedin_url,
                'preferred_role': request.preferred_role,
                'submitted_at': waitlist_entry.submitted_at
            }
            
            # Send confirmation to user
            user_email_result = await notify_job_waitlist_confirmation(
                waitlist_data=waitlist_data,
                graph_client=graph_client
            )
            
            if user_email_result['status'] == 'failed':
                print(f"⚠️ User confirmation email failed: {user_email_result.get('error')}")
            
            # Notify admin team
            admin_email_result = await notify_admin_new_waitlist_signup(
                waitlist_data=waitlist_data,
                graph_client=graph_client,
                admin_emails=ADMIN_EMAILS
            )
            
            if admin_email_result['status'] == 'failed':
                print(f"⚠️ Admin notification email failed: {admin_email_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send emails: {str(email_error)}")
            traceback.print_exc()
        
        return JobWaitlistResponse(
            message="Successfully joined the waitlist! We'll notify you when new roles open up.",
            waitlist_id=waitlist_entry.waitlist_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in job waitlist: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/job-waitlist")
async def get_job_waitlist(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = True,
    notified: Optional[bool] = None,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all job waitlist entries (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(JobWaitlist).order_by(JobWaitlist.submitted_at.desc())
        
        if is_active is not None:
            query = query.where(JobWaitlist.is_active == is_active)
        
        if notified is not None:
            query = query.where(JobWaitlist.notified == notified)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        return {
            "waitlist": [
                {
                    "waitlist_id": entry.waitlist_id,
                    "full_name": entry.full_name,
                    "email": entry.email,
                    "phone_number": entry.phone_number,
                    "linkedin_url": entry.linkedin_url,
                    "preferred_role": entry.preferred_role,
                    "notified": entry.notified,
                    "is_active": entry.is_active,
                    "submitted_at": entry.submitted_at.isoformat()
                }
                for entry in entries
            ],
            "total": len(entries),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching waitlist: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch waitlist entries."
        )


@router.patch("/job-waitlist/{waitlist_id}/notify")
async def mark_waitlist_as_notified(
    waitlist_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Mark a waitlist entry as notified (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(JobWaitlist).where(JobWaitlist.waitlist_id == waitlist_id)
        result = await db.execute(query)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        entry.notified = True
        await db.commit()
        
        return {"message": "Waitlist entry marked as notified", "waitlist_id": waitlist_id}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update waitlist entry")
    
"""
Add this endpoint to your app/routes/ideation_jobs_and_careers.py file
"""

@router.post("/jobs/{job_id}/notify-waitlisters")
async def notify_waitlisters_of_new_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Notify all active job waitlisters about a new job opening.
    Sends personalized emails to waitlisters whose preferred role matches the job.
    
    TODO: Add proper admin authorization check.
    """
    try:
        # Get the job
        job_query = select(Job).where(Job.job_id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only allow notifying for open jobs
        if job.status != JobStatus.OPEN:
            raise HTTPException(
                status_code=400,
                detail="Can only notify waitlisters about open positions"
            )
        
        # Get all active waitlisters who haven't been notified yet
        waitlist_query = select(JobWaitlist).where(
            and_(
                JobWaitlist.is_active == True,
                JobWaitlist.notified == False
            )
        ).order_by(JobWaitlist.submitted_at.asc())
        
        waitlist_result = await db.execute(waitlist_query)
        waitlisters = waitlist_result.scalars().all()
        
        if not waitlisters:
            return {
                "message": "No active waitlisters to notify",
                "job_id": job_id,
                "job_title": job.title,
                "notified_count": 0
            }
        
        # Prepare job data
        job_data = {
            'job_id': job.job_id,
            'title': job.title,
            'description': job.description,
            'tags': job.tags,
            'location': job.location,
            'employment_type': job.employment_type,
            'experience_level': job.experience_level,
            'salary_range': job.salary_range
        }
        
        graph_client = get_graph_root_client()
        
        successful_notifications = 0
        failed_notifications = 0
        notification_results = []
        
        for waitlister in waitlisters:
            try:
                waitlister_data = {
                    'email': waitlister.email,
                    'full_name': waitlister.full_name,
                    'preferred_role': waitlister.preferred_role,
                    'waitlist_id': waitlister.waitlist_id
                }
                
                # Send email notification
                email_result = await notify_waitlisters_new_job(
                    job_data=job_data,
                    waitlister_data=waitlister_data,
                    graph_client=graph_client
                )
                
                if email_result['status'] == 'sent':
                    # Mark as notified
                    waitlister.notified = True
                    successful_notifications += 1
                    notification_results.append({
                        'email': waitlister.email,
                        'status': 'sent'
                    })
                else:
                    failed_notifications += 1
                    notification_results.append({
                        'email': waitlister.email,
                        'status': 'failed',
                        'error': email_result.get('error')
                    })
                
            except Exception as e:
                print(f"⚠️ Error notifying {waitlister.email}: {str(e)}")
                failed_notifications += 1
                notification_results.append({
                    'email': waitlister.email,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Commit the changes to mark waitlisters as notified
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error committing waitlist updates: {traceback.format_exc()}")
        
        return {
            "message": f"Notification process completed. {successful_notifications} emails sent successfully.",
            "job_id": job_id,
            "job_title": job.title,
            "total_waitlisters": len(waitlisters),
            "successful_notifications": successful_notifications,
            "failed_notifications": failed_notifications,
            "details": notification_results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error notifying waitlisters: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while notifying waitlisters."
        )


@router.post("/jobs/{job_id}/reset-waitlist-notifications")
async def reset_waitlist_notifications(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Reset the 'notified' flag for all waitlisters, allowing them to be notified again.
    Useful if you want to re-notify waitlisters about an important job update.
    
    TODO: Add proper admin authorization check.
    """
    try:
        # Verify job exists
        job_query = select(Job).where(Job.job_id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Reset all waitlisters' notified flag
        update_query = select(JobWaitlist).where(
            and_(
                JobWaitlist.is_active == True,
                JobWaitlist.notified == True
            )
        )
        
        result = await db.execute(update_query)
        waitlisters = result.scalars().all()
        
        reset_count = 0
        for waitlister in waitlisters:
            waitlister.notified = False
            reset_count += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully reset notification status for {reset_count} waitlisters",
            "job_id": job_id,
            "job_title": job.title,
            "reset_count": reset_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        error_traceback = traceback.format_exc()
        print(f"Error resetting waitlist notifications: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reset waitlist notifications"
        )

@router.post("/reset-all-waitlist-notifications")
async def reset_all_waitlist_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Reset the 'notified' flag for ALL waitlisters across all jobs.
    This is a global reset - use with caution!
    
    Useful scenarios:
    - System-wide notification campaigns
    - After major platform updates
    - When you have multiple new jobs to announce
    
    TODO: Add proper admin authorization check.
    """
    try:
        # Get ALL active waitlisters who have been notified
        update_query = select(JobWaitlist).where(
            and_(
                JobWaitlist.is_active == True,
                JobWaitlist.notified == True
            )
        )
        
        result = await db.execute(update_query)
        waitlisters = result.scalars().all()
        
        reset_count = 0
        for waitlister in waitlisters:
            waitlister.notified = False
            reset_count += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully reset notification status for all waitlisters system-wide",
            "reset_count": reset_count,
            "scope": "global"
        }
    
    except Exception as e:
        await db.rollback()
        error_traceback = traceback.format_exc()
        print(f"Error resetting all waitlist notifications: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reset waitlist notifications"
        ) 

@router.post("/becoming-the-first", response_model=BecomingTheFirstResponse)
async def submit_becoming_the_first_registration(
    request: BecomingTheFirstRequest,
    db: AsyncSession = Depends(aget_db)
):
    """Submit registration for Becoming The First event."""
    try:
        # Normalize email
        normalized_email = normalize_email(request.email)
        
        # Get the Becoming The First event ID (assuming it's been created)

        becoming_first_event_id = 2  # Replace with actual event ID
        
        # Check for duplicate submission
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=DUPLICATE_SUBMISSION_WINDOW)
            
            query = select(BecomingTheFirstAttendance).where(
                and_(
                    BecomingTheFirstAttendance.email == normalized_email,
                    BecomingTheFirstAttendance.event_id == becoming_first_event_id,
                    BecomingTheFirstAttendance.submitted_at >= cutoff_time
                )
            )
            
            result = await db.execute(query)
            existing_registration = result.scalar_one_or_none()
            
            if existing_registration:
                raise HTTPException(
                    status_code=409,
                    detail="You're already registered for this event! Check your email for confirmation."
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in duplicate check: {traceback.format_exc()}")
            # Continue if duplicate check fails
        
        # Validate required fields
        if not request.full_name.strip():
            raise HTTPException(status_code=400, detail="Full name is required")
        
        if not request.location.strip():
            raise HTTPException(status_code=400, detail="Location is required")
        
        if not request.current_role:
            raise HTTPException(status_code=400, detail="Current role is required")
        
        if not request.fields_of_interest or len(request.fields_of_interest) == 0:
            raise HTTPException(status_code=400, detail="At least one field of interest is required")
        
        if len(request.why_attend) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Please provide more detail about why you want to attend (minimum 10 characters)"
            )
        
        if len(request.learning_expectations) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Please provide more detail about your learning expectations (minimum 10 characters)"
            )
        
        # Convert fields_of_interest to JSON string
        fields_of_interest_json = json.dumps(request.fields_of_interest)
        
        # Create registration
        registration = BecomingTheFirstAttendance(
            registration_id=str(uuid.uuid4()),
            full_name=request.full_name.strip(),
            email=normalized_email,
            contact_number=request.contact_number.strip() if request.contact_number else None,
            location=request.location.strip(),
            current_role=request.current_role,
            fields_of_interest=fields_of_interest_json,
            why_attend=request.why_attend.strip(),
            learning_expectations=request.learning_expectations.strip(),
            referral_source=request.referral_source,
            referral_source_other=request.referral_source_other.strip() if request.referral_source_other else None,
            receive_updates=request.receive_updates,
            event_id=becoming_first_event_id,
            status="registered",
            submitted_at=datetime.utcnow()
        )
        
        db.add(registration)
        
        try:
            await db.commit()
            await db.refresh(registration)
        except Exception as e:
            await db.rollback()
            print(f"Database commit error: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save your registration. Please try again later."
            )
        
        # Send confirmation emails
        try:
            graph_client = get_graph_root_client()
            registration_data = {
                'email': normalized_email,
                'full_name': request.full_name,
                'registration_id': registration.registration_id,
                'event_date': 'Wednesday, December 10th, 2025',
                'event_time': '7:00 PM GMT',
                'event_location': 'Online Event',
                'submitted_at': registration.submitted_at,
                "meeting_link": "https://calendar.app.google/4ZFaaEVMZKCDU6hS6"
            }
            
            # Send confirmation to user
            user_email_result = await notify_becoming_first_registration_confirmation(
                registration_data=registration_data,
                graph_client=graph_client
            )
            
            if user_email_result['status'] == 'failed':
                print(f"⚠️ User confirmation email failed: {user_email_result.get('error')}")
            
            # Notify admin team
            admin_email_result = await notify_admin_new_becoming_first_registration(
                registration_data={
                    **registration_data,
                    'contact_number': request.contact_number,
                    'location': request.location,
                    'current_role': request.current_role,
                    'fields_of_interest': request.fields_of_interest,
                    'why_attend': request.why_attend,
                    'learning_expectations': request.learning_expectations,
                    'referral_source': request.referral_source,
                    'receive_updates': request.receive_updates
                },
                graph_client=graph_client,
                admin_emails=ADMIN_EMAILS
            )
            
            if admin_email_result['status'] == 'failed':
                print(f"⚠️ Admin notification email failed: {admin_email_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send emails: {str(email_error)}")
            traceback.print_exc()
        
        return BecomingTheFirstResponse(
            message="Registration successful! Check your email for event details and the link to join.",
            registration_id=registration.registration_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in Becoming The First registration: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/becoming-the-first/registrations")
async def get_becoming_first_registrations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all Becoming The First registrations (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(BecomingTheFirstAttendance).order_by(
            BecomingTheFirstAttendance.submitted_at.desc()
        )
        
        if status:
            query = query.where(BecomingTheFirstAttendance.status == status)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        registrations = result.scalars().all()
        
        return {
            "registrations": [
                {
                    "registration_id": reg.registration_id,
                    "full_name": reg.full_name,
                    "email": reg.email,
                    "contact_number": reg.contact_number,
                    "location": reg.location,
                    "current_role": reg.current_role,
                    "fields_of_interest": json.loads(reg.fields_of_interest),
                    "why_attend": reg.why_attend,
                    "learning_expectations": reg.learning_expectations,
                    "referral_source": reg.referral_source,
                    "referral_source_other": reg.referral_source_other,
                    "receive_updates": reg.receive_updates,
                    "status": reg.status,
                    "submitted_at": reg.submitted_at.isoformat()
                }
                for reg in registrations
            ],
            "total": len(registrations),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching registrations: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch registrations."
        )


@router.patch("/becoming-the-first/registrations/{registration_id}/confirm")
async def confirm_becoming_first_registration(
    registration_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Confirm a registration (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(BecomingTheFirstAttendance).where(
            BecomingTheFirstAttendance.registration_id == registration_id
        )
        result = await db.execute(query)
        registration = result.scalar_one_or_none()
        
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        registration.confirm_registration()
        await db.commit()
        
        return {
            "message": "Registration confirmed",
            "registration_id": registration_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to confirm registration")
    

@router.post("/axi-launch", response_model=AxiLaunchResponse)
async def submit_axi_launch_registration(
    request: AxiLaunchRequest,
    db: AsyncSession = Depends(aget_db)
):
    """Submit registration for AXI Launch event."""
    try:
         # Normalize email
        normalized_email = normalize_email(request.email)
        
        # Get the AXI Launch event ID
        axi_launch_event_id = 1
        
        # Check for duplicate submission
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=DUPLICATE_SUBMISSION_WINDOW)
            
            query = select(AxiLaunchAttendance).where(
                and_(
                    AxiLaunchAttendance.email == normalized_email,
                    AxiLaunchAttendance.event_id == axi_launch_event_id,
                    AxiLaunchAttendance.submitted_at >= cutoff_time
                )
            )
            
            result = await db.execute(query)
            existing_registration = result.scalar_one_or_none()
            
            if existing_registration:
                raise HTTPException(
                    status_code=409,
                    detail="You're already registered for this event! Check your email for confirmation."
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in duplicate check: {traceback.format_exc()}")
            # Continue if duplicate check fails
        
        # Validate required fields
        if not request.full_name.strip():
            raise HTTPException(status_code=400, detail="Full name is required")
        
        if not request.location.strip():
            raise HTTPException(status_code=400, detail="Location is required")
        
        if not request.current_role:
            raise HTTPException(status_code=400, detail="Current role is required")
        
        if len(request.why_attend) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Please provide more detail about why you want to attend (minimum 10 characters)"
            )
        
        if len(request.networking_goals) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Please provide more detail about your networking goals (minimum 10 characters)"
            )
        
        # Generate registration ID
        registration_id = str(uuid.uuid4())
        
        # Generate QR code with logo
        try:
            qr_result = generate_axi_launch_qr_code(
                registration_id=registration_id,
                event_id=axi_launch_event_id,
                attendee_email=normalized_email,
                attendee_name=request.full_name,
                logo_path="app/static/images/yellow-logo.png",  # Update path as needed
                base_url=f'{settings.FRONTEND_URL}/events/event-axi-launch-2026/axi-verify'
            )
            qr_code_base64 = qr_result["qr_code_base64"]
            qr_code_data = qr_result["qr_code_data"]
        except Exception as qr_error:
            print(f"⚠️ QR code generation failed: {str(qr_error)}")
            qr_code_base64 = None
            qr_code_data = None
        
        # Create registration
        registration = AxiLaunchAttendance(
            registration_id=registration_id,
            full_name=request.full_name.strip(),
            email=normalized_email,
            contact_number=request.contact_number.strip() if request.contact_number else None,
            location=request.location.strip(),
            current_role=request.current_role,
            current_role_other=request.current_role_other.strip() if request.current_role_other else None,
            builder_type=request.builder_type,
            builder_type_other=request.builder_type_other.strip() if request.builder_type_other else None,
            experience_level=request.experience_level,
            startup_stage=request.startup_stage,
            startup_name=request.startup_name.strip() if request.startup_name else None,
            investor_type=request.investor_type,
            investment_focus=request.investment_focus.strip() if request.investment_focus else None,
            expertise_areas=request.expertise_areas.strip() if request.expertise_areas else None,
            organization_name=request.organization_name.strip() if request.organization_name else None,
            why_attend=request.why_attend.strip(),
            networking_goals=request.networking_goals.strip(),
            referral_source=request.referral_source,
            referral_source_other=request.referral_source_other.strip() if request.referral_source_other else None,
            receive_updates=request.receive_updates,
            qr_code=qr_code_base64,
            qr_code_data=qr_code_data,
            event_id=axi_launch_event_id,
            status="registered",
            submitted_at=datetime.utcnow()
        )
        
        db.add(registration)
        
        try:
            await db.commit()
            await db.refresh(registration)
        except Exception as e:
            await db.rollback()
            print(f"Database commit error: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save your registration. Please try again later."
            )
        
        # Generate ticket PDF
        ticket_pdf = None
        if qr_code_base64:
            try:
                ticket_pdf = await generate_axi_launch_ticket_pdf({
                    'registration_id': registration.registration_id,
                    'event_name': 'AXI Launch',  # Update with actual event name
                    'event_date': '7th February, 2026',
                    'event_time': '9 AM',  # Update with actual time
                    'venue_name': 'University of Ghana, Lego',  # Update with actual venue
                    'venue_address': 'TBD',  # Update with actual address
                    'attendee_name': request.full_name,
                    'attendee_email': normalized_email,
                    'current_role': request.current_role,
                    'qr_code_base64': qr_code_base64
                })
            except Exception as pdf_error:
                print(f"⚠️ Ticket PDF generation failed: {str(pdf_error)}")
                ticket_pdf = None
        
        # Send confirmation emails
        try:
            graph_client = get_graph_client()
            registration_data = {
                'email': normalized_email,
                'full_name': request.full_name,
                'registration_id': registration.registration_id,
                'event_date': '7th February, 2026',
                'event_time': '9 AM',
                'event_location': 'University of Ghana, Lego',
                'submitted_at': registration.submitted_at,
                'ticket_pdf': ticket_pdf
            }
            
            # Send confirmation to user
            user_email_result = await notify_axi_launch_registration_confirmation(
                registration_data=registration_data,
                graph_client=graph_client
            )
            
            if user_email_result['status'] == 'failed':
                print(f"⚠️ User confirmation email failed: {user_email_result.get('error')}")
            
            # Notify admin team
            admin_email_result = await notify_admin_new_axi_launch_registration(
                registration_data={
                    **registration_data,
                    'contact_number': request.contact_number,
                    'location': request.location,
                    'current_role': request.current_role,
                    'current_role_other': request.current_role_other,
                    'builder_type': request.builder_type,
                    'builder_type_other': request.builder_type_other,
                    'experience_level': request.experience_level,
                    'startup_stage': request.startup_stage,
                    'startup_name': request.startup_name,
                    'investor_type': request.investor_type,
                    'investment_focus': request.investment_focus,
                    'expertise_areas': request.expertise_areas,
                    'organization_name': request.organization_name,
                    'why_attend': request.why_attend,
                    'networking_goals': request.networking_goals,
                    'referral_source': request.referral_source,
                    'receive_updates': request.receive_updates
                },
                graph_client=graph_client,
                admin_emails=ADMIN_EMAILS
            )
            
            if admin_email_result['status'] == 'failed':
                print(f"⚠️ Admin notification email failed: {admin_email_result.get('error')}")
                
        except Exception as email_error:
            print(f"⚠️ Failed to send emails: {str(email_error)}")
            traceback.print_exc()
        
        return AxiLaunchResponse(
            message="Registration successful! Check your email for your ticket and event details.",
            registration_id=registration.registration_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in AXI Launch registration: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/axi-launch/registrations")
async def get_axi_launch_registrations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all AXI Launch registrations (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(AxiLaunchAttendance).order_by(
            AxiLaunchAttendance.submitted_at.desc()
        )
        
        if status:
            query = query.where(AxiLaunchAttendance.status == status)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        registrations = result.scalars().all()
        
        return {
            "registrations": [
                {
                    "registration_id": reg.registration_id,
                    "full_name": reg.full_name,
                    "email": reg.email,
                    "contact_number": reg.contact_number,
                    "location": reg.location,
                    "current_role": reg.current_role,
                    "current_role_other": reg.current_role_other,
                    "builder_type": reg.builder_type,
                    "builder_type_other": reg.builder_type_other,
                    "experience_level": reg.experience_level,
                    "startup_stage": reg.startup_stage,
                    "startup_name": reg.startup_name,
                    "investor_type": reg.investor_type,
                    "investment_focus": reg.investment_focus,
                    "expertise_areas": reg.expertise_areas,
                    "organization_name": reg.organization_name,
                    "why_attend": reg.why_attend,
                    "networking_goals": reg.networking_goals,
                    "referral_source": reg.referral_source,
                    "referral_source_other": reg.referral_source_other,
                    "receive_updates": reg.receive_updates,
                    "status": reg.status,
                    "submitted_at": reg.submitted_at.isoformat()
                }
                for reg in registrations
            ],
            "total": len(registrations),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching registrations: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch registrations."
        )


@router.patch("/axi-launch/registrations/{registration_id}/confirm")
async def confirm_axi_launch_registration(
    registration_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Confirm a registration (admin endpoint).
    TODO: Add authentication/authorization for admin access.
    """
    try:
        query = select(AxiLaunchAttendance).where(
            AxiLaunchAttendance.registration_id == registration_id
        )
        result = await db.execute(query)
        registration = result.scalar_one_or_none()
        
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        registration.confirm_registration()
        await db.commit()
        
        return {
            "message": "Registration confirmed",
            "registration_id": registration_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to confirm registration")
    
@router.post("/axi-launch/verify-qr")
async def verify_axi_launch_qr_code(
    registration_id: str = Form(...),
    event_id: int = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Verify a QR code and automatically check in the attendee.
    Requires authenticated staff user.
    
    Form Parameters:
        registration_id: The registration ID to verify
        event_id: The event ID
        email: Attendee's email
        name: Attendee's name
        type: Should be "axi_launch_registration"
    """
    try:
        # Validate the type
        if type != "axi_launch_registration":
            raise HTTPException(
                status_code=400,
                detail="This QR code is not for AXI Launch event"
            )
        
        # Get registration from database
        query = select(AxiLaunchAttendance).where(
            AxiLaunchAttendance.registration_id == registration_id
        )
        result = await db.execute(query)
        registration = result.scalar_one_or_none()
        
        if not registration:
            raise HTTPException(
                status_code=404,
                detail="Registration not found"
            )
        
        # Verify email matches
        if registration.email.lower() != email.lower():
            raise HTTPException(
                status_code=400,
                detail="Registration details do not match"
            )
        
        # Check if cancelled
        if registration.status == "cancelled":
            raise HTTPException(
                status_code=400,
                detail="This registration has been cancelled"
            )
        
        # Check if already checked in
        already_checked_in = registration.status == "attended"
        
        # Perform check-in if not already checked in
        if not already_checked_in:
            registration.mark_attended()
            await db.commit()
            await db.refresh(registration)
        
        # Return attendee info with check-in status
        return {
            "valid": True,
            "registration_id": registration.registration_id,
            "full_name": registration.full_name,
            "email": registration.email,
            "current_role": registration.current_role,
            "location": registration.location,
            "status": registration.status,
            "already_checked_in": already_checked_in,
            "checked_in_at": registration.attended_at.isoformat() if registration.attended_at else None,
            "checked_in_by_name": f"{current_user.first_name} {current_user.last_name}" if not already_checked_in else None,
            "registered_at": registration.submitted_at.isoformat(),
            "event_details": {
                "name": "AXI Launch",
                "date": "7th February, 2026",
                "time": "9 AM",
                "venue": "University of Ghana, Legon"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error verifying QR code: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify QR code"
        )


@router.post("/axi-launch/check-in/{registration_id}")
async def check_in_axi_launch_attendee(
    registration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Check in an attendee using their registration ID (from QR code).
    Marks them as attended.
    Requires authenticated staff user.
    """
    try:
        query = select(AxiLaunchAttendance).where(
            AxiLaunchAttendance.registration_id == registration_id
        )
        result = await db.execute(query)
        registration = result.scalar_one_or_none()
        
        if not registration:
            raise HTTPException(
                status_code=404,
                detail="Registration not found"
            )
        
        if registration.status == "attended":
            return {
                "message": "Attendee already checked in",
                "registration_id": registration_id,
                "checked_in_at": registration.attended_at.isoformat(),
                "already_checked_in": True,
                "attendee_name": registration.full_name,
                "attendee_email": registration.email
            }
        
        # Mark as attended
        registration.mark_attended()
        await db.commit()
        await db.refresh(registration)
        
        return {
            "message": "Check-in successful",
            "registration_id": registration_id,
            "full_name": registration.full_name,
            "email": registration.email,
            "current_role": registration.current_role,
            "checked_in_at": registration.attended_at.isoformat(),
            "checked_in_by_name": f"{current_user.first_name} {current_user.last_name}",
            "already_checked_in": False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error during check-in: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check in attendee"
        )
    
@router.get("/becoming-the-first/stats")
async def get_becoming_the_first_stats(
    page: int = Query(1, ge=1, description="Page number for attendee responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get statistics and attendee data for Becoming The First event.
    Requires authenticated user.
    
    Returns:
    - Total attendees count
    - Role distribution
    - Referral source distribution
    - Fields of interest distribution
    - Paginated attendee expectations and reasons for attending
    """
    try:
        # Get all registrations for the event
        query = select(BecomingTheFirstAttendance).where(
            BecomingTheFirstAttendance.event_id == 2  # Becoming The First event
        )
        result = await db.execute(query)
        all_registrations = result.scalars().all()
        
        total_attendees = len(all_registrations)
        
        # Role distribution
        role_counts = {}
        for reg in all_registrations:
            role = reg.current_role
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_distribution = [
            {"name": role, "value": count}
            for role, count in role_counts.items()
        ]
        
        # Referral source distribution
        referral_counts = {}
        for reg in all_registrations:
            source = reg.referral_source
            if source == "Other" and reg.referral_source_other:
                source = f"Other: {reg.referral_source_other}"
            referral_counts[source] = referral_counts.get(source, 0) + 1
        
        referral_distribution = [
            {"name": source, "value": count}
            for source, count in sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Fields of interest distribution (parse JSON)
        interest_counts = {}
        for reg in all_registrations:
            try:
                import json
                interests = json.loads(reg.fields_of_interest) if isinstance(reg.fields_of_interest, str) else reg.fields_of_interest
                if isinstance(interests, list):
                    for interest in interests:
                        interest_counts[interest] = interest_counts.get(interest, 0) + 1
            except:
                # If not JSON, treat as single interest
                interest_counts[reg.fields_of_interest] = interest_counts.get(reg.fields_of_interest, 0) + 1
        
        interest_distribution = [
            {"name": interest, "value": count}
            for interest, count in sorted(interest_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Status distribution
        status_counts = {}
        for reg in all_registrations:
            status = reg.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        status_distribution = [
            {"name": status.title(), "value": count}
            for status, count in status_counts.items()
        ]
        
        # Paginated attendee responses
        total_responses = total_attendees
        total_pages = (total_responses + page_size - 1) // page_size
        
        # Get paginated responses
        offset = (page - 1) * page_size
        responses_query = select(BecomingTheFirstAttendance).where(
            BecomingTheFirstAttendance.event_id == 2
        ).order_by(BecomingTheFirstAttendance.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()
        
        attendee_responses = [
            {
                "id": resp.registration_id,
                "name": resp.full_name,
                "location": resp.location,
                "role": resp.current_role,
                "why_attend": resp.why_attend,
                "learning_expectations": resp.learning_expectations,
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None
            }
            for resp in responses
        ]
        
        return {
            "event": {
                "id": 2,
                "slug": "becoming-the-first-leadership-conversation-2025",
                "title": "Becoming The First - Leadership Conversation"
            },
            "summary": {
                "total_attendees": total_attendees,
            },
            "statistics": {
                "roles": role_distribution,
                "referral_sources": referral_distribution,
                "interests": interest_distribution,
                "status": status_distribution
            },
            "responses": {
                "data": attendee_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_responses,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }
    
    except Exception as e:
        print(f"Error fetching Becoming The First stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch event statistics"
        )

@router.get("/axi-launch/stats")
async def get_axi_launch_stats(
    page: int = Query(1, ge=1, description="Page number for attendee responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get comprehensive statistics for AXI Launch event (event_id=1).
    Combines data from both paid tickets (EventTicket) and free registrations (AxiLaunchAttendance).
    
    Returns:
    - Total attendees (paid + free)
    - Ticket tier distribution
    - Status distribution
    - Role distribution
    - Referral source distribution
    - Builder type distribution (for developers)
    - Experience level distribution
    - Startup stage distribution (for founders)
    - Investor type distribution
    - Revenue statistics (total, by tier)
    - Paginated attendee responses
    """
    try:
        from sqlalchemy.orm import selectinload
        
        # Get event details
        event_query = select(PublicEvent).where(PublicEvent.id == 1)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get all paid tickets WITH eager loading of ticket_type relationship
        tickets_query = select(EventTicket).options(
            selectinload(EventTicket.ticket_type)
        ).where(EventTicket.event_id == 1)
        tickets_result = await db.execute(tickets_query)
        all_tickets = tickets_result.scalars().all()
        
        # Get all free registrations
        free_reg_query = select(AxiLaunchAttendance).where(AxiLaunchAttendance.event_id == 1)
        free_reg_result = await db.execute(free_reg_query)
        all_free_registrations = free_reg_result.scalars().all()
        
        # Calculate summary statistics
        total_paid_tickets = len(all_tickets)
        total_free_registrations = len(all_free_registrations)
        total_attendees = total_paid_tickets + total_free_registrations
        
        # Paid ticket statistics
        confirmed_tickets = sum(1 for t in all_tickets if t.status == TicketStatus.CONFIRMED)
        checked_in_tickets = sum(1 for t in all_tickets if t.checked_in)
        pending_tickets = sum(1 for t in all_tickets if t.status == TicketStatus.PENDING)
        cancelled_tickets = sum(1 for t in all_tickets if t.status == TicketStatus.CANCELLED)
        
        # Free registration statistics
        confirmed_free = sum(1 for r in all_free_registrations if r.status == "confirmed")
        attended_free = sum(1 for r in all_free_registrations if r.status == "attended")
        registered_free = sum(1 for r in all_free_registrations if r.status == "registered")
        
        # Ticket tier distribution (paid only)
        tier_counts = {}
        for ticket in all_tickets:
            if ticket.ticket_type:
                tier = ticket.ticket_type.tier.value
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Add FREE tier for free registrations
        tier_counts["FREE"] = total_free_registrations
        
        tier_distribution = [
            {"name": tier, "value": count}
            for tier, count in sorted(tier_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Overall status distribution
        status_counts = {
            "Confirmed": confirmed_tickets + confirmed_free,
            "Checked In": checked_in_tickets + attended_free,
            "Pending": pending_tickets + registered_free,
            "Cancelled": cancelled_tickets
        }
        
        status_distribution = [
            {"name": status, "value": count}
            for status, count in status_counts.items() if count > 0
        ]
        
        # Role distribution (from free registrations)
        role_counts = {}
        for reg in all_free_registrations:
            role = reg.current_role
            if role == "Other" and reg.current_role_other:
                role = f"Other: {reg.current_role_other}"
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_distribution = [
            {"name": role, "value": count}
            for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Referral source distribution
        referral_counts = {}
        for reg in all_free_registrations:
            source = reg.referral_source
            if source == "Other" and reg.referral_source_other:
                source = f"Other: {reg.referral_source_other}"
            referral_counts[source] = referral_counts.get(source, 0) + 1
        
        referral_distribution = [
            {"name": source, "value": count}
            for source, count in sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Builder type distribution (for developers)
        builder_counts = {}
        for reg in all_free_registrations:
            if reg.builder_type:
                builder_type = reg.builder_type
                if builder_type == "Other" and reg.builder_type_other:
                    builder_type = f"Other: {reg.builder_type_other}"
                builder_counts[builder_type] = builder_counts.get(builder_type, 0) + 1
        
        builder_distribution = [
            {"name": builder_type, "value": count}
            for builder_type, count in sorted(builder_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Experience level distribution
        experience_counts = {}
        for reg in all_free_registrations:
            if reg.experience_level:
                experience_counts[reg.experience_level] = experience_counts.get(reg.experience_level, 0) + 1
        
        experience_distribution = [
            {"name": level, "value": count}
            for level, count in sorted(experience_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Startup stage distribution (for founders)
        startup_stage_counts = {}
        for reg in all_free_registrations:
            if reg.startup_stage:
                startup_stage_counts[reg.startup_stage] = startup_stage_counts.get(reg.startup_stage, 0) + 1
        
        startup_stage_distribution = [
            {"name": stage, "value": count}
            for stage, count in sorted(startup_stage_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Investor type distribution
        investor_counts = {}
        for reg in all_free_registrations:
            if reg.investor_type:
                investor_counts[reg.investor_type] = investor_counts.get(reg.investor_type, 0) + 1
        
        investor_distribution = [
            {"name": inv_type, "value": count}
            for inv_type, count in sorted(investor_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Revenue statistics (paid tickets only)
        total_revenue = sum(float(ticket.price_paid) for ticket in all_tickets if ticket.status == TicketStatus.CONFIRMED)
        
        revenue_by_tier = {}
        for ticket in all_tickets:
            if ticket.status == TicketStatus.CONFIRMED and ticket.ticket_type:
                tier = ticket.ticket_type.tier.value
                revenue_by_tier[tier] = revenue_by_tier.get(tier, 0) + float(ticket.price_paid)
        
        revenue_by_tier_distribution = [
            {"name": tier, "value": round(revenue, 2)}
            for tier, revenue in sorted(revenue_by_tier.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Paginated attendee responses (free registrations)
        total_responses = len(all_free_registrations)
        total_pages = (total_responses + page_size - 1) // page_size
        
        # Get paginated responses
        offset = (page - 1) * page_size
        responses_query = select(AxiLaunchAttendance).where(
            AxiLaunchAttendance.event_id == 1
        ).order_by(AxiLaunchAttendance.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()
        
        attendee_responses = [
            {
                "id": resp.registration_id,
                "name": resp.full_name,
                "email": resp.email,
                "location": resp.location,
                "role": resp.current_role,
                "builder_type": resp.builder_type,
                "experience_level": resp.experience_level,
                "startup_stage": resp.startup_stage,
                "startup_name": resp.startup_name,
                "investor_type": resp.investor_type,
                "why_attend": resp.why_attend,
                "networking_goals": resp.networking_goals,
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
                "status": resp.status
            }
            for resp in responses
        ]
        
        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None
            },
            "summary": {
                "total_attendees": total_attendees,
                "total_paid": total_paid_tickets,
                "total_free": total_free_registrations,
                "confirmed": confirmed_tickets + confirmed_free,
                "checked_in": checked_in_tickets + attended_free,
                "pending": pending_tickets + registered_free,
                "cancelled": cancelled_tickets,
                "total_revenue": round(total_revenue, 2)
            },
            "statistics": {
                "tiers": tier_distribution,
                "status": status_distribution,
                "roles": role_distribution,
                "referral_sources": referral_distribution,
                "builder_types": builder_distribution,
                "experience_levels": experience_distribution,
                "startup_stages": startup_stage_distribution,
                "investor_types": investor_distribution,
                "revenue_by_tier": revenue_by_tier_distribution
            },
            "responses": {
                "data": attendee_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_responses,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }
    
    except Exception as e:
        print(f"Error fetching AXI Launch stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch event statistics"
        )
    


@router.get("/events/{event_id}/volunteer-applications/stats")
async def get_volunteer_applications_stats(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number for responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get statistics for volunteer applications for a specific event.
    """
    try:
        # Get event details
        event_query = select(PublicEvent).where(PublicEvent.id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get all volunteer applications for the event
        base_query = select(VolunteerApplication).where(
            VolunteerApplication.event_id == event_id
        )
        
        # Execute for total count
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_applications = count_result.scalar_one()

        # Calculate age range distribution
        age_query = select(
            VolunteerApplication.age_range,
            func.count(VolunteerApplication.age_range)
        ).where(
            VolunteerApplication.event_id == event_id
        ).group_by(VolunteerApplication.age_range)
        
        age_result = await db.execute(age_query)
        age_distribution = [
            {"name": age_range[0].value if age_range[0] else "Not specified", "value": age_range[1]}
            for age_range in age_result.all()
        ]

        # Calculate volunteer roles distribution (parse JSON)
        all_applications_result = await db.execute(
            select(VolunteerApplication.volunteer_roles)
        )
        all_applications = all_applications_result.scalars().all()
        
        role_counts = {}
        for app in all_applications:
            try:
                roles = json.loads(app) if isinstance(app, str) else app
                if isinstance(roles, list):
                    for role in roles:
                        role_counts[role] = role_counts.get(role, 0) + 1
            except:
                continue
        
        role_distribution = [
            {"name": role, "value": count}
            for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Availability distribution
        availability_query = select(
            VolunteerApplication.availability,
            func.count(VolunteerApplication.availability)
        ).where(
            VolunteerApplication.event_id == event_id
        ).group_by(VolunteerApplication.availability)
        
        availability_result = await db.execute(availability_query)
        availability_distribution = [
            {"name": avail[0].value if avail[0] else "Not specified", "value": avail[1]}
            for avail in availability_result.all()
        ]

        # Skills analysis (word cloud data)
        skills_query = select(VolunteerApplication.skills).where(
            VolunteerApplication.event_id == event_id
        )
        skills_result = await db.execute(skills_query)
        skill_texts = skills_result.scalars().all()
        
        # Simple word frequency analysis
        word_counts = {}
        for text in skill_texts:
            if text:
                words = text.lower().split(',')
                for word in words:
                    word = word.strip()
                    if word:
                        word_counts[word] = word_counts.get(word, 0) + 1
        
        skill_distribution = [
            {"name": word, "value": count}
            for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20]  # Top 20
        ]

        # Referral source distribution
        referral_query = select(
            VolunteerApplication.how_heard_about_axi,
            func.count(VolunteerApplication.how_heard_about_axi)
        ).where(
            VolunteerApplication.event_id == event_id
        ).group_by(VolunteerApplication.how_heard_about_axi)
        
        referral_result = await db.execute(referral_query)
        referral_distribution = [
            {"name": source[0] or "Not specified", "value": source[1]}
            for source in referral_result.all()
        ]

        # Paginated responses
        total_pages = (total_applications + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        responses_query = select(VolunteerApplication).where(
            VolunteerApplication.event_id == event_id
        ).order_by(VolunteerApplication.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()

        application_responses = [
            {
                "registration_id": app.application_id,
                "full_name": app.full_name,
                "email": app.email,
                "phone_number": app.phone_number,
                "current_role": app.current_role,
                "age_range": app.age_range.value if app.age_range else None,
                "volunteer_roles": json.loads(app.volunteer_roles) if isinstance(app.volunteer_roles, str) else app.volunteer_roles,
                "why_volunteer": app.why_volunteer,
                "skills": app.skills,
                "availability": app.availability.value if app.availability else None,
                "ambassador_interest": app.ambassador_interest,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
            }
            for app in responses
        ]

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None
            },
            "summary": {
                "total_applications": total_applications,
                "by_status": {}  # Volunteer applications don't have status in model
            },
            "statistics": {
                "age_ranges": age_distribution,
                "volunteer_roles": role_distribution,
                "availability": availability_distribution,
                "skills": skill_distribution,
                "referral_sources": referral_distribution
            },
            "responses": {
                "data": application_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_applications,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }

    except Exception as e:
        print(f"Error fetching volunteer applications stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch volunteer application statistics"
        )


@router.get("/events/{event_id}/speaker-applications/stats")
async def get_speaker_applications_stats(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number for responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get statistics for speaker applications for a specific event.
    """
    try:
        # Get event details
        event_query = select(PublicEvent).where(PublicEvent.id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get all speaker applications for the event
        base_query = select(SpeakerApplication).where(
            SpeakerApplication.event_id == event_id
        )
        
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_applications = count_result.scalar_one()

        # Speaking formats distribution
        all_applications_result = await db.execute(
            select(SpeakerApplication.speaking_formats)
        )
        all_applications = all_applications_result.scalars().all()
        
        format_counts = {}
        for app in all_applications:
            try:
                formats = json.loads(app) if isinstance(app, str) else app
                if isinstance(formats, list):
                    for fmt in formats:
                        format_counts[fmt] = format_counts.get(fmt, 0) + 1
            except:
                continue
        
        format_distribution = [
            {"name": fmt, "value": count}
            for fmt, count in sorted(format_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Country distribution
        country_query = select(
            SpeakerApplication.country,
            func.count(SpeakerApplication.country)
        ).where(
            SpeakerApplication.event_id == event_id
        ).group_by(SpeakerApplication.country)
        
        country_result = await db.execute(country_query)
        country_distribution = [
            {"name": country[0] or "Not specified", "value": country[1]}
            for country in country_result.all()
        ]

        # Expertise analysis (from role_organization and proposal_topic)
        expertise_query = select(
            SpeakerApplication.role_organization,
            SpeakerApplication.proposal_topic
        ).where(SpeakerApplication.event_id == event_id)
        
        expertise_result = await db.execute(expertise_query)
        expertise_data = expertise_result.all()
        
        expertise_counts = {}
        for role, topic in expertise_data:
            if role:
                expertise_counts[role] = expertise_counts.get(role, 0) + 1
        
        expertise_distribution = [
            {"name": exp, "value": count}
            for exp, count in sorted(expertise_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]

        # Referral source distribution
        referral_query = select(
            SpeakerApplication.how_heard_about_axi,
            func.count(SpeakerApplication.how_heard_about_axi)
        ).where(
            SpeakerApplication.event_id == event_id
        ).group_by(SpeakerApplication.how_heard_about_axi)
        
        referral_result = await db.execute(referral_query)
        referral_distribution = [
            {"name": source[0] or "Not specified", "value": source[1]}
            for source in referral_result.all()
        ]

        # Paginated responses
        total_pages = (total_applications + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        responses_query = select(SpeakerApplication).where(
            SpeakerApplication.event_id == event_id
        ).order_by(SpeakerApplication.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()

        application_responses = [
            {
                "application_id": app.application_id,
                "full_name": app.full_name,
                "email": app.email,
                "phone_number": app.phone_number,
                "role_organization": app.role_organization,
                "country": app.country,
                "proposal_topic": app.proposal_topic,
                "speaking_formats": json.loads(app.speaking_formats) if isinstance(app.speaking_formats, str) else app.speaking_formats,
                "why_speak": app.why_speak,
                "short_bio": app.short_bio,
                "previous_engagements": app.previous_engagements,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
            }
            for app in responses
        ]

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None
            },
            "summary": {
                "total_applications": total_applications,
                "by_status": {}
            },
            "statistics": {
                "speaking_formats": format_distribution,
                "countries": country_distribution,
                "expertise_areas": expertise_distribution,
                "referral_sources": referral_distribution
            },
            "responses": {
                "data": application_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_applications,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }

    except Exception as e:
        print(f"Error fetching speaker applications stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch speaker application statistics"
        )


@router.get("/events/{event_id}/sponsorship-applications/stats")
async def get_sponsorship_applications_stats(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number for responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get statistics for sponsorship applications for a specific event.
    """
    try:
        # Get event details
        event_query = select(PublicEvent).where(PublicEvent.id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get all sponsorship applications for the event
        base_query = select(SponsorshipApplication).where(
            SponsorshipApplication.event_id == event_id
        )
        
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_applications = count_result.scalar_one()

        # Sponsorship tiers distribution
        all_applications_result = await db.execute(
            select(SponsorshipApplication.sponsorship_tiers)
        )
        all_applications = all_applications_result.scalars().all()
        
        tier_counts = {}
        for app in all_applications:
            try:
                tiers = json.loads(app) if isinstance(app, str) else app
                if isinstance(tiers, list):
                    for tier in tiers:
                        tier_counts[tier] = tier_counts.get(tier, 0) + 1
            except:
                continue
        
        tier_distribution = [
            {"name": tier, "value": count}
            for tier, count in sorted(tier_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Industry distribution
        industry_query = select(
            SponsorshipApplication.industry,
            func.count(SponsorshipApplication.industry)
        ).where(
            SponsorshipApplication.event_id == event_id
        ).group_by(SponsorshipApplication.industry)
        
        industry_result = await db.execute(industry_query)
        industry_distribution = [
            {"name": industry[0] or "Not specified", "value": industry[1]}
            for industry in industry_result.all()
        ]

        # Booth interest distribution
        booth_query = select(
            SponsorshipApplication.booth_interest,
            func.count(SponsorshipApplication.booth_interest)
        ).where(
            SponsorshipApplication.event_id == event_id
        ).group_by(SponsorshipApplication.booth_interest)
        
        booth_result = await db.execute(booth_query)
        booth_distribution = [
            {"name": "Yes" if booth[0] else "No", "value": booth[1]}
            for booth in booth_result.all()
        ]

        # Referral source distribution
        referral_query = select(
            SponsorshipApplication.how_heard_about_axi,
            func.count(SponsorshipApplication.how_heard_about_axi)
        ).where(
            SponsorshipApplication.event_id == event_id
        ).group_by(SponsorshipApplication.how_heard_about_axi)
        
        referral_result = await db.execute(referral_query)
        referral_distribution = [
            {"name": source[0] or "Not specified", "value": source[1]}
            for source in referral_result.all()
        ]

        # Organization types (from industry)
        org_type_distribution = industry_distribution  # Using industry as proxy

        # Paginated responses
        total_pages = (total_applications + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        responses_query = select(SponsorshipApplication).where(
            SponsorshipApplication.event_id == event_id
        ).order_by(SponsorshipApplication.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()

        application_responses = [
            {
                "application_id": app.application_id,
                "organization_name": app.organization_name,
                "industry": app.industry,
                "contact_person_name": app.contact_person_name,
                "email": app.email,
                "phone_number": app.phone_number,
                "sponsorship_tiers": json.loads(app.sponsorship_tiers) if isinstance(app.sponsorship_tiers, str) else app.sponsorship_tiers,
                "sponsorship_goals": app.sponsorship_goals,
                "booth_interest": app.booth_interest,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
            }
            for app in responses
        ]

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None
            },
            "summary": {
                "total_applications": total_applications,
                "by_status": {}
            },
            "statistics": {
                "sponsorship_tiers": tier_distribution,
                "industries": industry_distribution,
                "booth_interest": booth_distribution,
                "referral_sources": referral_distribution,
                "organization_types": org_type_distribution
            },
            "responses": {
                "data": application_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_applications,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }

    except Exception as e:
        print(f"Error fetching sponsorship applications stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch sponsorship application statistics"
        )


@router.get("/events/{event_id}/partnership-applications/stats")
async def get_partnership_applications_stats(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number for responses"),
    page_size: int = Query(10, ge=1, le=50, description="Number of responses per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get statistics for partnership applications for a specific event.
    """
    try:
        # Get event details
        event_query = select(PublicEvent).where(PublicEvent.id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get all partnership applications for the event
        base_query = select(PartnershipApplication).where(
            PartnershipApplication.event_id == event_id
        )
        
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_applications = count_result.scalar_one()

        # Organization type distribution
        org_type_query = select(
            PartnershipApplication.organization_type,
            func.count(PartnershipApplication.organization_type)
        ).where(
            PartnershipApplication.event_id == event_id
        ).group_by(PartnershipApplication.organization_type)
        
        org_type_result = await db.execute(org_type_query)
        org_type_distribution = [
            {"name": org_type[0].value if org_type[0] else "Not specified", "value": org_type[1]}
            for org_type in org_type_result.all()
        ]

        # Partnership types distribution
        all_applications_result = await db.execute(
            select(PartnershipApplication.partnership_types)
        )
        all_applications = all_applications_result.scalars().all()
        
        partnership_counts = {}
        for app in all_applications:
            try:
                types = json.loads(app) if isinstance(app, str) else app
                if isinstance(types, list):
                    for p_type in types:
                        partnership_counts[p_type] = partnership_counts.get(p_type, 0) + 1
            except:
                continue
        
        partnership_distribution = [
            {"name": p_type, "value": count}
            for p_type, count in sorted(partnership_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Value propositions analysis (from value_to_bring)
        value_query = select(PartnershipApplication.value_to_bring).where(
            PartnershipApplication.event_id == event_id
        )
        value_result = await db.execute(value_query)
        value_texts = value_result.scalars().all()
        
        # Simple keyword analysis for value propositions
        value_keywords = ["innovation", "collaboration", "technology", "network", "resources", 
                         "expertise", "growth", "development", "community", "impact"]
        
        keyword_counts = {keyword: 0 for keyword in value_keywords}
        for text in value_texts:
            if text:
                text_lower = text.lower()
                for keyword in value_keywords:
                    if keyword in text_lower:
                        keyword_counts[keyword] += 1
        
        value_distribution = [
            {"name": keyword, "value": count}
            for keyword, count in keyword_counts.items() if count > 0
        ]

        # Referral source distribution
        referral_query = select(
            PartnershipApplication.referrer,
            func.count(PartnershipApplication.referrer)
        ).where(
            PartnershipApplication.event_id == event_id
        ).group_by(PartnershipApplication.referrer)
        
        referral_result = await db.execute(referral_query)
        referral_distribution = [
            {"name": source[0] or "Not specified", "value": source[1]}
            for source in referral_result.all()
        ]

        # Paginated responses
        total_pages = (total_applications + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        responses_query = select(PartnershipApplication).where(
            PartnershipApplication.event_id == event_id
        ).order_by(PartnershipApplication.submitted_at.desc()).offset(offset).limit(page_size)
        
        responses_result = await db.execute(responses_query)
        responses = responses_result.scalars().all()

        application_responses = [
            {
                "application_id": app.application_id,
                "organization_name": app.organization_name,
                "organization_type": app.organization_type.value if app.organization_type else None,
                "contact_person_name": app.contact_person_name,
                "email": app.email,
                "phone_number": app.phone_number,
                "partnership_types": json.loads(app.partnership_types) if isinstance(app.partnership_types, str) else app.partnership_types,
                "value_to_bring": app.value_to_bring,
                "value_to_receive": app.value_to_receive,
                "referrer": app.referrer,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
            }
            for app in responses
        ]

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "title": event.title,
                "event_date": event.event_date.isoformat() if event.event_date else None
            },
            "summary": {
                "total_applications": total_applications,
                "by_status": {}
            },
            "statistics": {
                "organization_types": org_type_distribution,
                "partnership_types": partnership_distribution,
                "value_propositions": value_distribution,
                "referral_sources": referral_distribution
            },
            "responses": {
                "data": application_responses,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_items": total_applications,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }

    except Exception as e:
        print(f"Error fetching partnership applications stats: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch partnership application statistics"
        )

@router.get("/partnership-proposals")
async def get_partnership_proposals(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(1000, ge=1, le=1000, description="Maximum number of records to return"),
    organization_type: Optional[str] = Query(None, description="Filter by organization type"),
    has_proposal: Optional[bool] = Query(None, description="Filter by proposal attachment"),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all partnership applications with or without proposals.
    Requires authenticated user with proper authorization.
    
    Query Parameters:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        organization_type: Filter by organization type (startup, corporate, ngo, government, other)
        has_proposal: Filter by whether proposal is attached (true/false)
        event_id: Filter by specific event ID
    
    Returns:
        List of partnership applications with all details
    """
    try:
        # Check authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view partnership proposals"
            )
        
        # Build base query with event relationship
        query = select(PartnershipApplication).options(
            selectinload(PartnershipApplication.event)
        )
        
        # Apply filters
        filters = []
        
        if organization_type:
            try:
                org_type_enum = OrganizationType(organization_type)
                filters.append(PartnershipApplication.organization_type == org_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid organization type: {organization_type}"
                )
        
        if has_proposal is not None:
            if has_proposal:
                filters.append(PartnershipApplication.proposal_url.isnot(None))
            else:
                filters.append(PartnershipApplication.proposal_url.is_(None))
        
        if event_id is not None:
            filters.append(PartnershipApplication.event_id == event_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Order by most recent first
        query = query.order_by(PartnershipApplication.submitted_at.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        applications = result.scalars().all()
        
        # Get total count for pagination info
        count_query = select(func.count()).select_from(PartnershipApplication)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()
        
        # Format response
        applications_list = []
        for app in applications:
            # Parse partnership_types JSON
            try:
                partnership_types = json.loads(app.partnership_types) if isinstance(app.partnership_types, str) else app.partnership_types
            except (json.JSONDecodeError, TypeError):
                partnership_types = []
            
            application_data = {
                "application_id": app.application_id,
                "organization_name": app.organization_name,
                "organization_type": app.organization_type.value if app.organization_type else None,
                "contact_person_name": app.contact_person_name,
                "phone_number": app.phone_number,
                "email": app.email,
                "linkedin_website": app.linkedin_website,
                "partnership_types": partnership_types,
                "other_reason": app.other_reason,
                "value_to_bring": app.value_to_bring,
                "value_to_receive": app.value_to_receive,
                "referrer": app.referrer,
                "proposal_url": app.proposal_url,
                "authorized_contact": app.authorized_contact,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
                "event_id": app.event_id,
                "event_title": app.event.title if app.event else None,
                "event_slug": app.event.slug if app.event else None,
                "event_date": app.event.event_date.isoformat() if app.event and app.event.event_date else None
            }
            applications_list.append(application_data)
        
        # Calculate statistics
        stats = {
            "total_applications": total_count,
            "with_proposals": sum(1 for app in applications if app.proposal_url),
            "without_proposals": sum(1 for app in applications if not app.proposal_url),
            "by_organization_type": {}
        }
        
        # Count by organization type
        for app in applications:
            org_type = app.organization_type.value if app.organization_type else "unknown"
            stats["by_organization_type"][org_type] = stats["by_organization_type"].get(org_type, 0) + 1
        
        return {
            "applications": applications_list,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "returned": len(applications_list)
            },
            "statistics": stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching partnership proposals: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch partnership proposals"
        )


@router.get("/partnership-proposals/summary")
async def get_partnership_proposals_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get summary statistics for partnership proposals.
    Requires authenticated user with proper authorization.
    
    Returns:
        Summary statistics including counts by organization type,
        partnership types distribution, proposals status, etc.
    """
    try:
        # Check authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view partnership proposals"
            )
        
        # Get all applications
        query = select(PartnershipApplication)
        result = await db.execute(query)
        all_applications = result.scalars().all()
        
        total_applications = len(all_applications)
        
        # Organization type distribution
        org_type_counts = {}
        for app in all_applications:
            org_type = app.organization_type.value if app.organization_type else "unknown"
            org_type_counts[org_type] = org_type_counts.get(org_type, 0) + 1
        
        org_type_distribution = [
            {"name": org_type.title(), "value": count}
            for org_type, count in sorted(org_type_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Partnership types distribution
        partnership_type_counts = {}
        for app in all_applications:
            try:
                types = json.loads(app.partnership_types) if isinstance(app.partnership_types, str) else app.partnership_types
                if isinstance(types, list):
                    for p_type in types:
                        partnership_type_counts[p_type] = partnership_type_counts.get(p_type, 0) + 1
            except:
                continue
        
        partnership_type_distribution = [
            {"name": p_type, "value": count}
            for p_type, count in sorted(partnership_type_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Proposals status
        with_proposals = sum(1 for app in all_applications if app.proposal_url)
        without_proposals = total_applications - with_proposals
        
        proposal_status = [
            {"name": "With Proposals", "value": with_proposals},
            {"name": "Without Proposals", "value": without_proposals}
        ]
        
        # Referral sources
        referral_counts = {}
        for app in all_applications:
            source = app.referrer or "Not specified"
            referral_counts[source] = referral_counts.get(source, 0) + 1
        
        referral_distribution = [
            {"name": source, "value": count}
            for source, count in sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Event association
        with_event = sum(1 for app in all_applications if app.event_id)
        without_event = total_applications - with_event
        
        event_association = [
            {"name": "Event-specific", "value": with_event},
            {"name": "General", "value": without_event}
        ]
        
        # Recent applications (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_applications = sum(
            1 for app in all_applications 
            if app.submitted_at and app.submitted_at >= cutoff_date
        )
        
        return {
            "summary": {
                "total_applications": total_applications,
                "with_proposals": with_proposals,
                "without_proposals": without_proposals,
                "recent_applications_30_days": recent_applications
            },
            "distributions": {
                "organization_types": org_type_distribution,
                "partnership_types": partnership_type_distribution,
                "proposal_status": proposal_status,
                "referral_sources": referral_distribution,
                "event_association": event_association
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching partnership proposals summary: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch partnership proposals summary"
        )


@router.get("/partnership-proposals/{application_id}")
async def get_partnership_proposal_details(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get detailed information about a specific partnership application.
    Requires authenticated user with proper authorization.
    """
    try:
        # Check authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view partnership proposals"
            )
        
        # Get application
        query = select(PartnershipApplication).options(
            selectinload(PartnershipApplication.event)
        ).where(PartnershipApplication.application_id == application_id)
        
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=404,
                detail="Partnership application not found"
            )
        
        # Parse partnership_types JSON
        try:
            partnership_types = json.loads(application.partnership_types) if isinstance(application.partnership_types, str) else application.partnership_types
        except (json.JSONDecodeError, TypeError):
            partnership_types = []
        
        return {
            "application_id": application.application_id,
            "organization_name": application.organization_name,
            "organization_type": application.organization_type.value if application.organization_type else None,
            "contact_person_name": application.contact_person_name,
            "phone_number": application.phone_number,
            "email": application.email,
            "linkedin_website": application.linkedin_website,
            "partnership_types": partnership_types,
            "other_reason": application.other_reason,
            "value_to_bring": application.value_to_bring,
            "value_to_receive": application.value_to_receive,
            "referrer": application.referrer,
            "proposal_url": application.proposal_url,
            "authorized_contact": application.authorized_contact,
            "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
            "event": {
                "id": application.event.id,
                "title": application.event.title,
                "slug": application.event.slug,
                "event_date": application.event.event_date.isoformat() if application.event.event_date else None
            } if application.event else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error fetching partnership proposal details: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch partnership proposal details"
        )