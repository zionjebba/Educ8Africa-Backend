"""Profile Update Culture Points Scheduler for IAxOS system."""

import asyncio
from datetime import datetime, time
import pytz
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import aget_db
from app.models.user import User

logger = logging.getLogger(__name__)

ACCRA_TIMEZONE = pytz.timezone('Africa/Accra')

# Schedule time: 2:10 PM Accra time
PROFILE_CHECK_HOUR = 14
PROFILE_CHECK_MINUTE = 20

# Points configuration
POINTS_PER_FIELD = 10
TOTAL_POSSIBLE_POINTS = 60  # 6 fields × 10 points


async def check_profile_completeness(user: User) -> tuple[bool, int, List[str]]:
    """
    Check if a user's profile is complete and calculate points.
    
    Returns:
        tuple: (is_complete, points_earned, completed_fields)
    """
    completed_fields = []
    points = 0
    
    # Check avatar (10 points)
    if user.avatar:
        completed_fields.append("avatar")
        points += POINTS_PER_FIELD
    
    # Check phone (10 points)
    if user.phone:
        completed_fields.append("phone")
        points += POINTS_PER_FIELD
    
    # Check location (10 points)
    if user.location:
        completed_fields.append("location")
        points += POINTS_PER_FIELD
    
    # Check skills - must have at least one skill (10 points)
    if user.skills and user.skills.strip():
        completed_fields.append("skills")
        points += POINTS_PER_FIELD
    
    # Check LinkedIn URL (10 points)
    if user.linkedin_url:
        completed_fields.append("linkedin_url")
        points += POINTS_PER_FIELD
    
    # Check booking link (10 points)
    if user.booking_link:
        completed_fields.append("booking_link")
        points += POINTS_PER_FIELD
    
    is_complete = points == TOTAL_POSSIBLE_POINTS
    
    return is_complete, points, completed_fields


async def award_profile_completion_points(db: AsyncSession) -> dict:
    """
    Award culture points to users who have completed their profiles.
    Only runs once per user (tracked by profile_points_awarded flag).
    
    Returns:
        dict: Summary of points awarded
    """
    logger.info("🎯 Starting profile completion points award process...")
    
    try:
        # Get all active users who haven't received profile completion points yet
        result = await db.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.profile_points_awarded == False
                )
            )
        )
        users = result.scalars().all()
        
        logger.info(f"📊 Found {len(users)} users to check for profile completion")
        
        awarded_users = []
        partial_users = []
        incomplete_users = []
        total_points_awarded = 0
        
        for user in users:
            is_complete, points_earned, completed_fields = await check_profile_completeness(user)
            
            if points_earned > 0:
                # Award the points
                user.culture_points += points_earned
                user.profile_points_awarded = True
                user.profile_completion_points = points_earned
                
                total_points_awarded += points_earned
                
                if is_complete:
                    awarded_users.append({
                        "user_id": user.user_id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "points_awarded": points_earned,
                        "completed_fields": completed_fields
                    })
                    logger.info(f"✅ {user.first_name} {user.last_name}: Full profile complete - {points_earned} points awarded")
                else:
                    partial_users.append({
                        "user_id": user.user_id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "points_awarded": points_earned,
                        "completed_fields": completed_fields,
                        "missing_fields": TOTAL_POSSIBLE_POINTS - points_earned
                    })
                    logger.info(f"⚠️ {user.first_name} {user.last_name}: Partial profile - {points_earned}/{TOTAL_POSSIBLE_POINTS} points awarded")
            else:
                incomplete_users.append({
                    "user_id": user.user_id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email
                })
                user.profile_points_awarded = True  # Mark as processed even if no points
                logger.info(f"❌ {user.first_name} {user.last_name}: No profile fields completed - 0 points")
        
        # Commit all changes
        await db.commit()
        
        summary = {
            "success": True,
            "timestamp": datetime.now(ACCRA_TIMEZONE).isoformat(),
            "total_users_checked": len(users),
            "fully_completed": len(awarded_users),
            "partially_completed": len(partial_users),
            "not_completed": len(incomplete_users),
            "total_points_awarded": total_points_awarded,
            "awarded_users": awarded_users,
            "partial_users": partial_users,
            "incomplete_users": incomplete_users
        }
        
        logger.info(f"✅ Profile points award process completed successfully")
        logger.info(f"📊 Summary: {len(awarded_users)} fully completed, {len(partial_users)} partially completed, {len(incomplete_users)} not completed")
        logger.info(f"💰 Total points awarded: {total_points_awarded}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error awarding profile completion points: {str(e)}")
        await db.rollback()
        raise


async def profile_points_scheduler():
    """
    Background task that checks once at 2:10 PM Accra time to award profile completion points.
    Only runs once on the scheduled day.
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("🚀 PROFILE COMPLETION POINTS SCHEDULER STARTING...")
        logger.info("="*80)
        logger.info(f"⏰ Scheduled for: {PROFILE_CHECK_HOUR:02d}:{PROFILE_CHECK_MINUTE:02d} Accra time")
        logger.info(f"🌍 Timezone: {ACCRA_TIMEZONE}")
        
        # Initial delay
        logger.info("⏳ Waiting 10 seconds before starting checks...")
        await asyncio.sleep(10)
        
        scheduled_time_reached = False
        
        while True:
            try:
                now = datetime.now(ACCRA_TIMEZONE)
                
                # Check if we've reached the scheduled time (2:10 PM)
                if (now.hour == PROFILE_CHECK_HOUR and 
                    now.minute == PROFILE_CHECK_MINUTE and 
                    not scheduled_time_reached):
                    
                    logger.info(f"\n🎯 SCHEDULED TIME REACHED: {now.strftime('%H:%M:%S')}")
                    logger.info("▶️  Executing profile completion points award...")
                    
                    # Execute the points award
                    async for db in aget_db():
                        try:
                            summary = await award_profile_completion_points(db)
                            
                            logger.info("\n" + "="*80)
                            logger.info("📊 PROFILE POINTS AWARD SUMMARY")
                            logger.info("="*80)
                            logger.info(f"Total users checked: {summary['total_users_checked']}")
                            logger.info(f"Fully completed: {summary['fully_completed']}")
                            logger.info(f"Partially completed: {summary['partially_completed']}")
                            logger.info(f"Not completed: {summary['not_completed']}")
                            logger.info(f"Total points awarded: {summary['total_points_awarded']}")
                            logger.info("="*80 + "\n")
                            
                            scheduled_time_reached = True
                            
                        except Exception as e:
                            logger.error(f"❌ Error during points award: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            break
                    
                    # After execution, the scheduler can continue running but won't execute again
                    logger.info("✅ Profile points award completed. Scheduler will now idle.")
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ SCHEDULER ERROR: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)
                
    except Exception as e:
        logger.error(f"❌❌❌ SCHEDULER INITIALIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()