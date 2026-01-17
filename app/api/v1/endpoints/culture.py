"""Culture Connection router for IAxOS system."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import uuid

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.event import Event, EventRSVP
from app.models.socialmatch import SocialMatch
from app.constants.constants import EventCategory

from app.schemas.eventSchema import RSVPRequest


router = APIRouter(
    prefix="/culture",
    tags=["culture"]
)


@router.get("/stats")
async def get_culture_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get culture statistics for the current user.
    Returns: culture points, events attended, connections made
    """
    # Get events attended (RSVPs with attending status)
    events_query = await db.execute(
        select(func.count(EventRSVP.rsvp_id))
        .where(
            EventRSVP.user_id == current_user.user_id,
            EventRSVP.status == "attending"
        )
    )
    events_attended = events_query.scalar() or 0
    
    # Get connections made (unique social matches)
    matches_query = await db.execute(
        select(func.count(SocialMatch.match_id))
        .where(
            or_(
                SocialMatch.user1_id == current_user.user_id,
                SocialMatch.user2_id == current_user.user_id
            ),
            SocialMatch.completed == True
        )
    )
    connections_made = matches_query.scalar() or 0
    
    return {
        "culture_points": current_user.culture_points or 0,
        "events_attended": events_attended,
        "connections_made": connections_made
    }


@router.get("/events")
async def get_upcoming_events(
    limit: int = Query(10, description="Number of events to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get upcoming events with RSVP information.
    """
    today = datetime.utcnow().date()
    
    # Get upcoming events
    events_query = await db.execute(
        select(Event)
        .where(Event.event_date >= today)
        .order_by(Event.event_date.asc(), Event.event_time.asc())
        .limit(limit)
        .options(joinedload(Event.rsvps))
    )
    events = events_query.scalars().unique().all()
    
    # Get user's RSVPs
    user_rsvps_query = await db.execute(
        select(EventRSVP)
        .where(EventRSVP.user_id == current_user.user_id)
    )
    user_rsvps = {rsvp.event_id: rsvp.status for rsvp in user_rsvps_query.scalars().all()}
    
    events_data = []
    for event in events:
        # Count attendees
        attendees_count = len([rsvp for rsvp in event.rsvps if rsvp.status == "attending"])
        
        # Determine icon and color based on category
        icon_map = {
            EventCategory.social: "users",
            EventCategory.learning: "sparkles",
            EventCategory.celebration: "trophy",
            EventCategory.wellness: "heart"
        }
        
        color_map = {
            EventCategory.social: {"icon": "text-blue-600", "bg": "bg-blue-100"},
            EventCategory.learning: {"icon": "text-purple-600", "bg": "bg-purple-100"},
            EventCategory.celebration: {"icon": "text-yellow-600", "bg": "bg-yellow-100"},
            EventCategory.wellness: {"icon": "text-green-600", "bg": "bg-green-100"}
        }
        
        events_data.append({
            "id": event.event_id,
            "title": event.title,
            "description": event.description,
            "date": event.event_date.strftime("%b %d, %Y"),
            "time": event.event_time,
            "attendees": attendees_count,
            "maxAttendees": event.max_attendees,
            "category": event.category.value,
            "icon": icon_map.get(event.category, "calendar"),
            "iconColor": color_map.get(event.category, {}).get("icon", "text-gray-600"),
            "iconBg": color_map.get(event.category, {}).get("bg", "bg-gray-100"),
            "location": event.location,
            "rsvpStatus": user_rsvps.get(event.event_id)
        })
    
    return {"events": events_data}


@router.post("/events/rsvp")
async def rsvp_to_event(
    rsvp_data: RSVPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    RSVP to an event or cancel RSVP.
    """
    # Check if event exists
    event_query = await db.execute(
        select(Event).where(Event.event_id == rsvp_data.event_id)
        .options(joinedload(Event.rsvps))
    )
    event = event_query.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if user already has an RSVP
    existing_rsvp_query = await db.execute(
        select(EventRSVP).where(
            EventRSVP.event_id == rsvp_data.event_id,
            EventRSVP.user_id == current_user.user_id
        )
    )
    existing_rsvp = existing_rsvp_query.scalar_one_or_none()
    
    if rsvp_data.status == "cancelled":
        if existing_rsvp:
            await db.delete(existing_rsvp)
            await db.commit()
            return {"message": "RSVP cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="No RSVP to cancel")
    
    # Check if event is full
    attendees_count = len([rsvp for rsvp in event.rsvps if rsvp.status == "attending"])
    if attendees_count >= event.max_attendees and not existing_rsvp:
        raise HTTPException(status_code=400, detail="Event is full")
    
    if existing_rsvp:
        existing_rsvp.status = rsvp_data.status
    else:
        new_rsvp = EventRSVP(
            rsvp_id=str(uuid.uuid4()),
            event_id=rsvp_data.event_id,
            user_id=current_user.user_id,
            status=rsvp_data.status,
            created_at=datetime.utcnow()
        )
        db.add(new_rsvp)
    
    if rsvp_data.status == "attending":
        current_user.culture_points += 10
    
    await db.commit()
    
    return {
        "message": f"RSVP updated to {rsvp_data.status}",
        "culture_points": current_user.culture_points
    }


@router.get("/social-matches")
async def get_social_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get this week's social matches for the current user.
    """
    today = datetime.utcnow().date()
    # Get Saturday of this week
    days_until_saturday = (5 - today.weekday()) % 7
    this_saturday = today + timedelta(days=days_until_saturday)
    
    # Get matches for this Saturday
    matches_query = await db.execute(
        select(SocialMatch)
        .where(
            or_(
                SocialMatch.user1_id == current_user.user_id,
                SocialMatch.user2_id == current_user.user_id
            ),
            SocialMatch.match_date == this_saturday
        )
        .options(
            joinedload(SocialMatch.user1).joinedload(User.department),
            joinedload(SocialMatch.user2).joinedload(User.department)
        )
    )
    matches = matches_query.scalars().unique().all()
    
    matches_data = []
    for match in matches:
        # Determine which user is the match (not current user)
        matched_user = match.user2 if match.user1_id == current_user.user_id else match.user1
        
        # Parse common interests
        interests = match.common_interests.split(',') if match.common_interests else []
        
        matches_data.append({
            "matchId": match.match_id,  # ← ADD THIS LINE
            "name": f"{matched_user.first_name} {matched_user.last_name}",
            "avatar": matched_user.avatar or f"https://ui-avatars.com/api/?name={matched_user.first_name}+{matched_user.last_name}",
            "department": matched_user.department.name if matched_user.department else "Unknown",
            "interests": [interest.strip() for interest in interests],
            "videoCallLink": match.video_call_link
        })
    
    return {"matches": matches_data}


@router.get("/leaderboard")
async def get_culture_leaderboard(
    limit: int = Query(10, description="Number of entries to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get culture leaderboard based on culture points and activity.
    """
    # Get top users by culture points
    users_query = await db.execute(
        select(User)
        .where(User.is_active == True)
        .order_by(User.culture_points.desc())
        .limit(limit)
    )
    users = users_query.scalars().all()
    
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        # Count activities (events attended + social matches completed)
        events_count_query = await db.execute(
            select(func.count(EventRSVP.rsvp_id))
            .where(
                EventRSVP.user_id == user.user_id,
                EventRSVP.status == "attending"
            )
        )
        events_count = events_count_query.scalar() or 0
        
        matches_count_query = await db.execute(
            select(func.count(SocialMatch.match_id))
            .where(
                or_(
                    SocialMatch.user1_id == user.user_id,
                    SocialMatch.user2_id == user.user_id
                ),
                SocialMatch.completed == True
            )
        )
        matches_count = matches_count_query.scalar() or 0
        
        total_activities = events_count + matches_count
        
        leaderboard.append({
            "rank": rank,
            "name": f"{user.first_name} {user.last_name}",
            "avatar": user.avatar or f"https://ui-avatars.com/api/?name={user.first_name}+{user.last_name}",
            "activities": total_activities,
            "points": user.culture_points or 0
        })
    
    return {"entries": leaderboard}

