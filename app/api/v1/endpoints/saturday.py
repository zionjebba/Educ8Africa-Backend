"""Culture Connection router for Educ8Africa system."""

import asyncio
from datetime import datetime, timedelta
import random
from typing import List
from fastapi import APIRouter, Depends
import pytz
from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import uuid

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.socialmatch import SocialMatch, utc_now

from app.schemas.socialSaturdaySchemas import CallRatingRequest
from app.services.MicrosoftGraphClient import MicrosoftGraphClient
from app.core.config import settings
from dotenv import load_dotenv

load_dotenv()

TESTING_MODE = settings.TESTING_MODE

router = APIRouter(
    prefix="/saturdays",
    tags=["saturdays"]
)




DRAW_TIMEZONE = pytz.timezone('Africa/Accra')

# TESTING TIMES: 12:00 AM and 12:05 AM
TESTING_FIRST_DRAW_HOUR = 11
TESTING_FIRST_DRAW_MINUTE = 14
TESTING_SECOND_DRAW_HOUR = 11
TESTING_SECOND_DRAW_MINUTE = 19 

# PRODUCTION TIMES
# Special times for today (Nov 10, 2025): 12 PM and 2 PM
SPECIAL_FIRST_DRAW_HOUR = 12
SPECIAL_FIRST_DRAW_MINUTE = 0
SPECIAL_SECOND_DRAW_HOUR = 15
SPECIAL_SECOND_DRAW_MINUTE = 0

# Regular Saturday times: 10 AM and 2 PM
REGULAR_FIRST_DRAW_HOUR = 12
REGULAR_FIRST_DRAW_MINUTE = 0
REGULAR_SECOND_DRAW_HOUR = 15
REGULAR_SECOND_DRAW_MINUTE = 0

# Set to True for testing, False for production



def get_draw_times_for_date(date: datetime):
    """Get draw times for a specific date."""
    if TESTING_MODE:
        first_draw = date.replace(
            hour=TESTING_FIRST_DRAW_HOUR, 
            minute=TESTING_FIRST_DRAW_MINUTE, 
            second=0, 
            microsecond=0
        )
        second_draw = date.replace(
            hour=TESTING_SECOND_DRAW_HOUR, 
            minute=TESTING_SECOND_DRAW_MINUTE, 
            second=0, 
            microsecond=0
        )
    else:
        is_special_saturday = (
            date.year == 2025 and 
            date.month == 11 and 
            date.day == 10 and 
            date.weekday() == 5
        )
        
        if is_special_saturday:
            first_draw = date.replace(
                hour=SPECIAL_FIRST_DRAW_HOUR, 
                minute=SPECIAL_FIRST_DRAW_MINUTE, 
                second=0, 
                microsecond=0
            )
            second_draw = date.replace(
                hour=SPECIAL_SECOND_DRAW_HOUR, 
                minute=SPECIAL_SECOND_DRAW_MINUTE, 
                second=0, 
                microsecond=0
            )
        else:
            first_draw = date.replace(
                hour=REGULAR_FIRST_DRAW_HOUR, 
                minute=REGULAR_FIRST_DRAW_MINUTE, 
                second=0, 
                microsecond=0
            )
            second_draw = date.replace(
                hour=REGULAR_SECOND_DRAW_HOUR, 
                minute=REGULAR_SECOND_DRAW_MINUTE, 
                second=0, 
                microsecond=0
            )
    
    return first_draw, second_draw

def get_next_saturday_draw_times():
    """Get the next Saturday's draw times."""
    now = datetime.now(DRAW_TIMEZONE)
    
    # Find next Saturday (or today if it's Saturday and before the draws)
    days_until_saturday = (5 - now.weekday()) % 7  # Saturday is 5
    
    # If it's Saturday, check if we've passed both draws
    if days_until_saturday == 0:
        first_draw, second_draw = get_draw_times_for_date(now)
        
        # If we haven't passed the last draw yet, use today
        if now < second_draw:
            return first_draw, second_draw
        else:
            # Passed both draws, move to next Saturday
            days_until_saturday = 7
    
    # Calculate next Saturday
    next_saturday = now + timedelta(days=days_until_saturday)
    return get_draw_times_for_date(next_saturday)


async def get_users_matched_in_draw(db: AsyncSession, match_date: datetime, draw_number: int) -> set:
    """Get all user IDs that have been matched in a specific draw today."""
    match_date_only = match_date.date() if hasattr(match_date, 'date') else match_date
    
    result = await db.execute(
        select(SocialMatch).where(
            and_(
                SocialMatch.match_date == match_date_only,
                SocialMatch.draw_number == draw_number
            )
        )
    )
    matches = result.scalars().all()
    
    matched_users = set()
    for match in matches:
        matched_users.add(match.user1_id)
        matched_users.add(match.user2_id)
    
    return matched_users

async def get_todays_first_draw_partner(user_id: str, match_date: datetime, db: AsyncSession) -> str | None:
    """Get the partner this user was matched with in today's first draw."""
    match_date_only = match_date.date() if hasattr(match_date, 'date') else match_date
    
    result = await db.execute(
        select(SocialMatch).where(
            and_(
                SocialMatch.match_date == match_date_only,
                SocialMatch.draw_number == 1,
                or_(
                    SocialMatch.user1_id == user_id,
                    SocialMatch.user2_id == user_id
                )
            )
        )
    )
    match = result.scalar_one_or_none()
    
    if match:
        return match.user2_id if match.user1_id == user_id else match.user1_id
    return None


# async def calculate_match_distribution(total_users: int) -> tuple:
#     """
#     Calculate how many matches should be in each draw.
#     Returns (first_draw_matches, second_draw_matches)
#     """
#     total_matches = total_users // 2
    
#     # Distribute matches: first draw gets ceiling, second gets floor
#     # Example: 10 users = 5 matches -> first=3, second=2
#     # Example: 9 users = 4 matches -> first=2, second=2
#     first_draw_matches = (total_matches + 1) // 2
#     second_draw_matches = total_matches // 2
    
#     return first_draw_matches, second_draw_matches


async def automatic_draw_trigger(db: AsyncSession, graph_client):
    """Automatically trigger match draw at scheduled time."""
    from app.models.user import User
    from app.models.socialmatch import SocialMatch
    
    now = datetime.now(DRAW_TIMEZONE)
    
    print(f"\n{'='*60}")
    print(f"🎯 DRAW TRIGGER CALLED at {now.strftime('%H:%M:%S')}")
    print(f"   Mode: {'TESTING' if TESTING_MODE else 'PRODUCTION'}")
    print(f"   Day: {now.strftime('%A, %B %d, %Y')}")
    
    # Only proceed if it's Saturday in production mode
    if not TESTING_MODE and now.weekday() != 5:
        print(f"   ⏭️  Not Saturday - skipping (weekday: {now.weekday()})")
        return None
    
    first_draw_time, second_draw_time = get_draw_times_for_date(now)
    print(f"   Scheduled draws: {first_draw_time.strftime('%H:%M')}, {second_draw_time.strftime('%H:%M')}")
    
    # Determine which draw to execute
    current_draw_time = None
    draw_name = None
    draw_number = None
    
    first_draw_diff = (now - first_draw_time).total_seconds()
    second_draw_diff = (now - second_draw_time).total_seconds()
    
    print(f"   Time diff - First: {int(first_draw_diff)}s, Second: {int(second_draw_diff)}s")
    
    # CRITICAL: Only trigger AFTER scheduled time and within 2-minute window
    if 0 <= first_draw_diff <= 120:
        if abs(first_draw_diff) < abs(second_draw_diff):
            current_draw_time = first_draw_time
            draw_name = "First Draw"
            draw_number = 1
        else:
            print(f"   ⏰ Closer to second draw - skipping first draw trigger")
            print(f"{'='*60}\n")
            return None
    elif 0 <= second_draw_diff <= 120:
        if abs(second_draw_diff) < abs(first_draw_diff):
            current_draw_time = second_draw_time
            draw_name = "Second Draw"
            draw_number = 2
        else:
            print(f"   ⏰ Closer to first draw - skipping second draw trigger")
            print(f"{'='*60}\n")
            return None
    
    if not current_draw_time:
        print(f"   ⏰ Outside draw window - no action taken")
        print(f"{'='*60}\n")
        return None
    
    print(f"   🎲 {draw_name} window detected!")
    
    # Check if THIS SPECIFIC draw was already completed
    already_completed = await check_draw_completed(
        current_draw_time, 
        draw_number,
        db
    )
    
    if already_completed:
        print(f"   ✓ {draw_name} already completed")
        print(f"{'='*60}\n")
        return None
    
    print(f"   ▶️  Executing {draw_name}...")
    
    match_saturday = now.date()
    print(f"   📅 Match date: {match_saturday.strftime('%A, %B %d, %Y')}")
    
    # Get total active users
    all_users = await get_available_users_for_matching(db)
    total_users = len(all_users)
    print(f"   👥 Total active users: {total_users}")
    

    
    # Determine how many pairs for this draw
    num_pairs = total_users // 2
    print(f"   🎯 Creating {num_pairs} pair(s) for {draw_name}")
    
    # NEW LOGIC: For first draw only, check for already matched users (safety)
    # For second draw, we want to match everyone again with different partners
    if draw_number == 1:
        already_matched = await get_users_matched_in_draw(db, now, draw_number=1)
        print(f"   ℹ️  Users already matched in Draw 1: {len(already_matched)}")
        exclude_users = already_matched
    else:
        # Second draw - don't exclude anyone, they should all be matched again
        exclude_users = set()
        first_draw_count = await get_users_matched_in_draw(db, now, draw_number=1)
        print(f"   ℹ️  Users matched in Draw 1: {len(first_draw_count)} - Re-matching with new partners")
    
    # Select pairs with updated logic
    pairs = await select_match_pairs(
        db, 
        num_pairs=num_pairs, 
        exclude_users=exclude_users,
        is_second_draw=(draw_number == 2),
        match_date=now
    )
    
    if not pairs:
        print(f"   ⚠️  No pairs available for matching")
        print(f"{'='*60}\n")
        return None
    
    print(f"   👥 Creating {len(pairs)} match(es) for {draw_name}...")
    
    created_matches = []
    for i, (user1, user2) in enumerate(pairs, 1):
        print(f"   {i}. Matching {user1.first_name} & {user2.first_name}...")
        match = await create_match_pair_with_teams_meeting(
            user1, user2, now, draw_number, db, graph_client
        )
        created_matches.append(match)
    
    await db.commit()
    
    print(f"   ✅ SUCCESS: {len(created_matches)} match(es) created for {draw_name}!")
    print(f"{'='*60}\n")
    
    return len(created_matches)

async def social_saturday_scheduler():
    """Background task that checks every 15 seconds if it's time to trigger a draw."""
    try:
        print("\n" + "="*80)
        print("🚀🚀🚀 SOCIAL SATURDAY SCHEDULER STARTING... 🚀🚀🚀")
        print("="*80)
        
        from app.core.config import settings
        from app.services import MicrosoftGraphClient
        from app.core.database import aget_db
        
        print(f"⏰ Mode: {'TESTING' if TESTING_MODE else 'PRODUCTION'}")
        print(f"🌍 Timezone: {DRAW_TIMEZONE}")
        
        # Initialize Microsoft Graph Client
        print("🔄 Initializing Microsoft Graph Client...")
        graph_client = MicrosoftGraphClient.MicrosoftGraphClient(
            tenant_id=settings.MICROSOFT_TENANT_ID,
            client_id=settings.MICROSOFT_CLIENT_ID,
            client_secret=settings.MICROSOFT_CLIENT_SECRET
        )
        print("✅ Microsoft Graph Client initialized")
        
        # Initial delay
        print("⏳ Waiting 10 seconds before starting checks...")
        await asyncio.sleep(10)
        
        now = datetime.now(DRAW_TIMEZONE)
        first_draw, second_draw = get_draw_times_for_date(now)
        print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 Today's draws scheduled for: {first_draw.strftime('%H:%M')}, {second_draw.strftime('%H:%M')}")
        print("🔄 Starting main loop - checking every 15 seconds...")
        print("="*80 + "\n")
        
        check_count = 0
    except Exception as e:
        print(f"\n❌❌❌ SCHEDULER INITIALIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    
    while True:
        try:
            check_count += 1
            print(f"\n{'~'*60}")
            print(f"🔄 Loop iteration #{check_count}")
            
            now = datetime.now(DRAW_TIMEZONE)
            print(f"⏰ Current time: {now.strftime('%H:%M:%S')}, Weekday: {now.weekday()}")
            
            # In production, only run on Saturdays
            if not TESTING_MODE and now.weekday() != 5:  # Saturday is 5
                if check_count % 4 == 0:  # Print every minute
                    print(f"⏰ Not Saturday - waiting...")
                print(f"💤 Sleeping 15 seconds...")
                await asyncio.sleep(15)
                continue
            
            print(f"✅ Day check passed (Testing: {TESTING_MODE}, Weekday: {now.weekday()})")
            
            first_draw, second_draw = get_draw_times_for_date(now)
            print(f"📅 Draw times: First={first_draw.strftime('%H:%M')}, Second={second_draw.strftime('%H:%M')}")
            
            # Calculate time differences
            first_diff = abs((now - first_draw).total_seconds())
            second_diff = abs((now - second_draw).total_seconds())
            
            print(f"⏱️  Time diff - First: {int(first_diff)}s ({int(first_diff/60)}m), Second: {int(second_diff)}s ({int(second_diff/60)}m)")
            
            # Check if we're within 2 minutes (120 seconds) of either draw
            is_near_first = first_diff <= 120
            is_near_second = second_diff <= 120
            
            print(f"🎯 Near first? {is_near_first}, Near second? {is_near_second}")
            
            # DEBUG: Always print when close to draw time
            if is_near_first or is_near_second or first_diff <= 300 or second_diff <= 300:
                print(f"\n🔍 [{now.strftime('%H:%M:%S')}] Debug - First: {int(first_diff)}s, Second: {int(second_diff)}s")
                print(f"   is_near_first: {is_near_first}, is_near_second: {is_near_second}")
            
            if is_near_first or is_near_second:
                draw_type = "First" if is_near_first else "Second"
                print(f"\n⚡⚡⚡ {draw_type} Draw Window Active!")
                print(f"   Time to first: {int(first_diff)}s, Time to second: {int(second_diff)}s")
                
                # Attempt the draw
                print(f"🔄 Getting database session...")
                async for db in aget_db():
                    try:
                        print(f"✅ Database session obtained")
                        print(f"🎲 Calling automatic_draw_trigger...")
                        result = await automatic_draw_trigger(db, graph_client)
                        if result:
                            print(f"✅✅✅ Draw completed: {result} matches created\n")
                        else:
                            print(f"⚠️ Draw returned None (might be already completed)\n")
                    except Exception as e:
                        print(f"❌❌❌ Draw execution error: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        print(f"🔚 Closing database session")
                        break
            else:
                print(f"⏰ Not in draw window yet")
            
            print(f"💤 Sleeping 15 seconds...")
            print(f"{'~'*60}\n")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"\n❌ SCHEDULER ERROR: {e}")
            import traceback
            traceback.print_exc()
            print()
            await asyncio.sleep(60)

async def check_draw_completed(
    draw_time: datetime, 
    draw_number: int,  # NEW PARAMETER
    db: AsyncSession
) -> bool:
    """
    Check if a specific draw was completed.
    Now checks for the specific draw_number to avoid confusion.
    """
    from app.models.socialmatch import SocialMatch
    
    draw_time_utc = draw_time.astimezone(pytz.UTC)
    
    # Use 2-minute window (matching the trigger window)
    draw_start_utc = (draw_time_utc - timedelta(minutes=2)).replace(tzinfo=None)
    draw_end_utc = (draw_time_utc + timedelta(minutes=2)).replace(tzinfo=None)
    
    result = await db.execute(
        select(func.count(SocialMatch.match_id)).where(
            and_(
                SocialMatch.created_at >= draw_start_utc,
                SocialMatch.created_at <= draw_end_utc,
                SocialMatch.draw_number == draw_number  # Check specific draw
            )
        )
    )
    count = result.scalar()
    
    if count > 0:
        print(f"   ✓ Found {count} matches for Draw {draw_number} near {draw_time.strftime('%H:%M')}")
    
    return count > 0

async def get_available_users_for_matching(db: AsyncSession) -> List[User]:
    """Get all active users available for matching."""
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    return list(result.scalars().all())


async def get_previous_matches(user_id: str, db: AsyncSession) -> set:
    """Get all user IDs that this user has been matched with before."""
    result = await db.execute(
        select(SocialMatch).where(
            or_(
                SocialMatch.user1_id == user_id,
                SocialMatch.user2_id == user_id
            )
        )
    )
    matches = result.scalars().all()
    
    matched_users = set()
    for match in matches:
        if match.user1_id == user_id:
            matched_users.add(match.user2_id)
        else:
            matched_users.add(match.user1_id)
    
    return matched_users


async def select_match_pairs(
    db: AsyncSession, 
    num_pairs: int = 2, 
    exclude_users: set = None,
    is_second_draw: bool = False,
    match_date: datetime = None
) -> List[tuple]:
    """
    Select pairs of users who haven't been matched before.
    
    Args:
        db: Database session
        num_pairs: Number of pairs to create
        exclude_users: Set of user IDs to exclude (for first draw only)
        is_second_draw: If True, ignore today's first draw matches
        match_date: Current match date (for second draw logic)
    """
    if exclude_users is None:
        exclude_users = set()
    
    users = await get_available_users_for_matching(db)
    
    # For FIRST draw: exclude users already matched today (shouldn't happen but safety check)
    # For SECOND draw: DON'T exclude anyone from first draw - we want to match them again!
    if is_second_draw:
        available_users = users  # Everyone is available again
        print(f"   📊 Second Draw - All {len(available_users)} users available for re-matching")
    else:
        available_users = [u for u in users if u.user_id not in exclude_users]
        print(f"   📊 First Draw - Available users: {len(available_users)} (excluded {len(exclude_users)})")
    
    if len(available_users) < 2:
        return []
    
    # Shuffle users for randomness
    random.shuffle(available_users)
    
    selected_pairs = []
    used_users = set()
    
    for user in available_users:
        if user.user_id in used_users:
            continue
        
        if len(selected_pairs) >= num_pairs:
            break
        
        # Get users this person has been matched with historically
        previous_matches = await get_previous_matches(user.user_id, db)
        
        # For second draw, also get who they were matched with in first draw TODAY
        if is_second_draw and match_date:
            first_draw_matches = await get_users_matched_in_draw(db, match_date, draw_number=1)
            # Get this user's partner from first draw
            first_draw_partner = await get_todays_first_draw_partner(user.user_id, match_date, db)
            if first_draw_partner:
                previous_matches.add(first_draw_partner)
                print(f"   🔄 {user.first_name} was matched with partner from Draw 1, avoiding repeat")
        
        # Find a partner who:
        # 1. Isn't the same user
        # 2. Hasn't been matched with this user before (including today's first draw)
        # 3. Isn't already used in this current draw
        for potential_partner in available_users:
            if (potential_partner.user_id != user.user_id and 
                potential_partner.user_id not in previous_matches and
                potential_partner.user_id not in used_users):
                
                selected_pairs.append((user, potential_partner))
                used_users.add(user.user_id)
                used_users.add(potential_partner.user_id)
                break
    
    return selected_pairs

@router.get("/social-saturday/status")
async def get_draw_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get the current status of Social Saturday match draws."""
    
    now = datetime.now(DRAW_TIMEZONE)
    is_saturday_today = now.weekday() == 5
    is_eligible_day = TESTING_MODE or is_saturday_today
    
    if is_eligible_day:
        today_first_draw, today_second_draw = get_draw_times_for_date(now)
        
        # Check each draw specifically
        first_completed = await check_draw_completed(today_first_draw, 1, db)
        second_completed = await check_draw_completed(today_second_draw, 2, db)
        
        if now < today_first_draw:
            next_draw = today_first_draw
            draw_number = 1
        elif now < today_second_draw:
            next_draw = today_second_draw
            draw_number = 2
        else:
            first_draw_time, second_draw_time = get_next_saturday_draw_times()
            next_draw = first_draw_time
            draw_number = 1
    else:
        first_completed = False
        second_completed = False
        first_draw_time, second_draw_time = get_next_saturday_draw_times()
        next_draw = first_draw_time
        draw_number = 1
        today_first_draw = first_draw_time
        today_second_draw = second_draw_time
    
    time_diff = next_draw - now
    hours = max(0, int(time_diff.total_seconds() // 3600))
    minutes = max(0, int((time_diff.total_seconds() % 3600) // 60))
    seconds = max(0, int(time_diff.total_seconds() % 60))
    
    return {
        "next_draw_time": next_draw.isoformat(),
        "draw_number": draw_number,
        "first_draw_completed": first_completed,
        "second_draw_completed": second_completed,
        "is_eligible_day": is_eligible_day,
        "time_until_draw": {
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds
        },
        "draw_times": {
            "first": today_first_draw.isoformat(),
            "second": today_second_draw.isoformat()
        }
    }

async def create_match_pair(user1: User, user2: User, match_date: datetime, db: AsyncSession) -> SocialMatch:
    """Create a match between two users."""
    common_interests = []
    if user1.skills and user2.skills:
        skills1 = set(user1.skills.lower().split(","))
        skills2 = set(user2.skills.lower().split(","))
        common_interests = list(skills1.intersection(skills2))
    
    if hasattr(match_date, 'tzinfo') and match_date.tzinfo is not None:
        match_date_naive = match_date.replace(tzinfo=None)
    else:
        match_date_naive = match_date
    
    match = SocialMatch(
        match_id=str(uuid.uuid4()),
        user1_id=user1.user_id,
        user2_id=user2.user_id,
        match_date=match_date_naive.date() if hasattr(match_date_naive, 'date') else match_date_naive,
        common_interests=",".join(common_interests) if common_interests else None,
        video_call_link=None,
        completed=False
    )
    
    db.add(match)
    return match

async def create_match_pair_with_teams_meeting(
    user1: User, 
    user2: User, 
    match_date: datetime,
    draw_number: int,  # NEW PARAMETER
    db: AsyncSession,
    graph_client: MicrosoftGraphClient
) -> SocialMatch:
    """Create a match between two users with a Teams meeting link."""
    
    common_interests = []
    if user1.skills and user2.skills:
        skills1 = set(user1.skills.lower().split(","))
        skills2 = set(user2.skills.lower().split(","))
        common_interests = list(skills1.intersection(skills2))
    
    if hasattr(match_date, 'tzinfo') and match_date.tzinfo is not None:
        match_date_naive = match_date.replace(tzinfo=None)
    else:
        match_date_naive = match_date
    
    # Create Teams meeting
    video_call_link = None
    try:
        meeting_subject = f"Social Saturday Draw {draw_number}: {user1.first_name} & {user2.first_name}"
        
        meeting_start = datetime.combine(match_date_naive, datetime.min.time().replace(hour=10))
        meeting_end = meeting_start + timedelta(hours=1)
        
        meeting = await graph_client.create_online_meeting(
            user_email="noreply@educ8africa.com" if TESTING_MODE else user1.email,
            subject=meeting_subject,
            start_time=meeting_start,
            end_time=meeting_end,
            participants=[user2.email]
        )
        
        video_call_link = meeting["join_url"]
        print(f"✅ Created Teams meeting for {user1.first_name} & {user2.first_name}")
        
    except Exception as e:
        print(f"⚠️ Failed to create Teams meeting: {e}")
    
    match = SocialMatch(
        match_id=str(uuid.uuid4()),
        user1_id=user1.user_id,
        user2_id=user2.user_id,
        match_date=match_date_naive.date() if hasattr(match_date_naive, 'date') else match_date_naive,
        common_interests=",".join(common_interests) if common_interests else None,
        video_call_link=video_call_link,
        draw_number=draw_number,  
        completed=False
    )
    
    db.add(match)
    return match

@router.get("/social-saturday/recent-matches")
async def get_recent_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get recent Social Saturday matches grouped by week with enhanced display info."""
    
    four_weeks_ago = datetime.now() - timedelta(days=28)
    
    result = await db.execute(
        select(SocialMatch)
        .options(
            joinedload(SocialMatch.user1).joinedload(User.department),
            joinedload(SocialMatch.user2).joinedload(User.department)
        )
        .where(SocialMatch.created_at >= four_weeks_ago)
        .order_by(SocialMatch.match_date.desc(), SocialMatch.created_at.desc())
    )
    matches = result.scalars().unique().all()
    
    from collections import defaultdict
    weeks = defaultdict(list)
    
    for match in matches:
        match_date = match.match_date
        week_start = match_date - timedelta(days=match_date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        weeks[week_key].append(match)
    
    formatted_weeks = []
    today = datetime.now().date()
    
    for week_start, week_matches in sorted(weeks.items(), reverse=True):
        week_start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        week_end_date = week_start_date + timedelta(days=6)
        saturday_date = week_start_date + timedelta(days=5)  # Saturday of that week
        
        # Determine if this is the current week
        is_current_week = week_start_date <= today <= week_end_date
        is_upcoming = saturday_date > today
        
        formatted_matches = []
        for match in week_matches:
            # Generate avatar URLs if not present
            user1_avatar = match.user1.avatar or f"https://ui-avatars.com/api/?name={match.user1.first_name}+{match.user1.last_name}&background=random"
            user2_avatar = match.user2.avatar or f"https://ui-avatars.com/api/?name={match.user2.first_name}+{match.user2.last_name}&background=random"
            
            is_past = match.match_date < today
            
            formatted_matches.append({
                "match_id": match.match_id,
                "pair": [
                    {
                        "user_id": match.user1.user_id,
                        "name": f"{match.user1.first_name} {match.user1.last_name}",
                        "firstName": match.user1.first_name,
                        "avatar": user1_avatar,
                        "department": match.user1.department.name if match.user1.department else "N/A",
                        "role": match.user1.role.value if match.user1.role else "Member"
                    },
                    {
                        "user_id": match.user2.user_id,
                        "name": f"{match.user2.first_name} {match.user2.last_name}",
                        "firstName": match.user2.first_name,
                        "avatar": user2_avatar,
                        "department": match.user2.department.name if match.user2.department else "N/A",
                        "role": match.user2.role.value if match.user2.role else "Member"
                    }
                ],
                "common_interests": [interest.strip() for interest in match.common_interests.split(",")] if match.common_interests else [],
                "video_call_link": match.video_call_link,
                "match_date": match.match_date.isoformat(),
                "completed": match.completed,
                "is_past": is_past,
                "created_at": match.created_at.isoformat() if match.created_at else None
            })
        
        formatted_weeks.append({
            "week_label": f"{saturday_date.strftime('%B %d, %Y')}",
            "week_range": f"{week_start_date.strftime('%b %d')} - {week_end_date.strftime('%b %d, %Y')}",
            "saturday_date": saturday_date.isoformat(),
            "is_current_week": is_current_week,
            "is_upcoming": is_upcoming,
            "match_count": len(formatted_matches),
            "matches": formatted_matches
        })
    
    return {
        "weeks": formatted_weeks,
        "total_matches": len(matches)
    }

@router.get("/all-matches")
async def get_all_matches_for_modal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get ALL social matches for this week formatted for the WhatsNewModal.
    Returns all matches (not filtered by current user).
    Accounts for TESTING_MODE to check today's date instead of just Saturdays.
    """
    now = datetime.now(pytz.timezone('Africa/Accra'))
    today = now.date()
    
    if TESTING_MODE:
        target_date = today
        print(f"[TESTING MODE] Checking matches for today: {target_date}")
    else:
        current_weekday = today.weekday()
        if current_weekday == 5:  # Is Saturday
            target_date = today
        else:
            days_until_saturday = (5 - current_weekday) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            target_date = today + timedelta(days=days_until_saturday)
        print(f"[PRODUCTION MODE] Checking matches for Saturday: {target_date}")
    
    print(f"[DEBUG] Current time: {now}")
    print(f"[DEBUG] Today: {today}, Weekday: {today.weekday()} ({today.strftime('%A')})")
    print(f"[DEBUG] Target date: {target_date}")
    
    matches_query = await db.execute(
        select(SocialMatch)
        .where(SocialMatch.match_date == target_date)
        .options(
            joinedload(SocialMatch.user1).joinedload(User.department),
            joinedload(SocialMatch.user2).joinedload(User.department)
        )
        .order_by(SocialMatch.created_at.desc())
    )
    matches = matches_query.scalars().unique().all()
    
    print(f"[DEBUG] Found {len(matches)} matches for {target_date}")
    
    # Debug: Show all match dates in database
    all_matches_query = await db.execute(
        select(SocialMatch.match_date, func.count(SocialMatch.match_id))
        .group_by(SocialMatch.match_date)
        .order_by(SocialMatch.match_date.desc())
    )
    all_dates = all_matches_query.all()
    print(f"[DEBUG] All match dates in database: {[(str(date), count) for date, count in all_dates]}")
    
    matches_data = []
    for match in matches:
        # Parse common interests
        interests = match.common_interests.split(',') if match.common_interests else []
        interests = [interest.strip() for interest in interests if interest.strip()]
        
        match_obj = {
            "match_id": match.match_id,
            "pair": [
                {
                    "user_id": match.user1.user_id,
                    "name": f"{match.user1.first_name} {match.user1.last_name}",
                    "firstName": match.user1.first_name,
                    "avatar": match.user1.avatar or f"https://ui-avatars.com/api/?name={match.user1.first_name}+{match.user1.last_name}&background=3b82f6&color=fff",
                    "department": match.user1.department.name if match.user1.department else "Unknown",
                    "role": match.user1.role.value if match.user1.role else "Member"
                },
                {
                    "user_id": match.user2.user_id,
                    "name": f"{match.user2.first_name} {match.user2.last_name}",
                    "firstName": match.user2.first_name,
                    "avatar": match.user2.avatar or f"https://ui-avatars.com/api/?name={match.user2.first_name}+{match.user2.last_name}&background=3b82f6&color=fff",
                    "department": match.user2.department.name if match.user2.department else "Unknown",
                    "role": match.user2.role.value if match.user2.role else "Member"
                }
            ],
            "common_interests": interests,
            "video_call_link": match.video_call_link,
            "match_date": match.match_date.isoformat(),
            "completed": match.completed
        }
        matches_data.append(match_obj)
        print(f"[DEBUG] Match {len(matches_data)}: {match.user1.first_name} & {match.user2.first_name}")
    
    print(f"[DEBUG] Returning {len(matches_data)} matches for {target_date}")
    return {
        "matches": matches_data,
        "target_date": target_date.isoformat(),
        "testing_mode": TESTING_MODE
    }

@router.post("/social-saturday/matches/{match_id}/rate")
async def rate_social_call(
    match_id: str,
    rating_data: CallRatingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Rate a completed social call and mark it as ended.
    Automatically marks the match as completed when both users have rated.
    Awards 20 culture points for rating.
    """
    # Find the match
    result = await db.execute(
        select(SocialMatch).where(SocialMatch.match_id == match_id)
    )
    match = result.scalar_one_or_none()
    
    if not match:
        return {"error": "Match not found"}, 404
    
    # Verify the current user is part of this match
    if current_user.user_id not in [match.user1_id, match.user2_id]:
        return {"error": "Unauthorized - you are not part of this match"}, 403
    
    # Check if user already rated
    is_user1 = current_user.user_id == match.user1_id
    if is_user1 and match.user1_rating is not None:
        return {"error": "You have already rated this call"}, 400
    if not is_user1 and match.user2_rating is not None:
        return {"error": "You have already rated this call"}, 400
    
    # Save the rating
    now = utc_now()
    if is_user1:
        match.user1_rating = rating_data.rating
        match.user1_feedback = rating_data.feedback
        match.user1_ended_at = now
    else:
        match.user2_rating = rating_data.rating
        match.user2_feedback = rating_data.feedback
        match.user2_ended_at = now
    
    current_user.culture_points += 20
    
    if match.is_fully_rated:
        match.completed = True
    
    await db.commit()
    await db.refresh(match)
    await db.refresh(current_user)
    
    return {
        "success": True,
        "message": "Rating submitted successfully",
        "match_completed": match.completed,
        "both_rated": match.is_fully_rated,
        "average_rating": match.average_rating,
        "points_awarded": 20,
        "total_culture_points": current_user.culture_points
    }

@router.get("/check-unseen-draws")
async def check_unseen_draws(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Check if there are new draws that the user hasn't seen yet.
    Returns true if there are matches created after the user's last_seen_draw_at.
    Accounts for TESTING_MODE to check today's date instead of just Saturdays.
    """
    now = datetime.now(DRAW_TIMEZONE)
    today = now.date()
    
    # Determine the target match date based on mode
    if TESTING_MODE:
        # In testing mode, check today regardless of day of week
        target_date = today
        print(f"[TESTING MODE] Checking draws for today: {target_date}")
    else:
        # In production mode, check current or next Saturday
        current_weekday = today.weekday()
        if current_weekday == 5:  # Is Saturday
            target_date = today
        else:
            # Calculate next Saturday
            days_until_saturday = (5 - current_weekday) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            target_date = today + timedelta(days=days_until_saturday)
        print(f"[PRODUCTION MODE] Checking draws for Saturday: {target_date}")
    
    # Get matches for the target date
    matches_query = await db.execute(
        select(SocialMatch)
        .where(SocialMatch.match_date == target_date)
        .order_by(SocialMatch.created_at.desc())
    )
    matches = matches_query.scalars().all()
    
    print(f"Found {len(matches)} matches for {target_date}")
    
    if not matches:
        return {
            "has_unseen_draws": False,
            "latest_draw_at": None,
            "user_last_seen_at": current_user.last_seen_draw_at.isoformat() if current_user.last_seen_draw_at else None,
            "match_count": 0,
            "target_date": target_date.isoformat(),
            "testing_mode": TESTING_MODE
        }
    
    # Get the most recent match creation time
    latest_match_time = max(match.created_at for match in matches)
    
    # If user has never seen a draw, or latest draw is after their last seen time
    has_unseen = (
        current_user.last_seen_draw_at is None or 
        latest_match_time > current_user.last_seen_draw_at
    )
    
    print(f"User last seen: {current_user.last_seen_draw_at}, Latest match: {latest_match_time}, Has unseen: {has_unseen}")
    
    return {
        "has_unseen_draws": has_unseen,
        "latest_draw_at": latest_match_time.isoformat(),
        "user_last_seen_at": current_user.last_seen_draw_at.isoformat() if current_user.last_seen_draw_at else None,
        "match_count": len(matches),
        "target_date": target_date.isoformat(),
        "testing_mode": TESTING_MODE
    }


@router.post("/mark-draws-seen")
async def mark_draws_seen(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Mark that the user has seen the latest draws.
    Updates the user's last_seen_draw_at timestamp.
    """
    now_utc = utc_now()
    current_user.last_seen_draw_at = now_utc
    await db.commit()
    await db.refresh(current_user)
    
    print(f"✓ User {current_user.first_name} {current_user.last_name} marked draws as seen at {now_utc}")
    
    return {
        "success": True,
        "last_seen_draw_at": current_user.last_seen_draw_at.isoformat(),
        "message": "Draws marked as seen successfully"
    }