"""Admin endpoints for system-wide operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.constants.constants import UserRole

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


@router.post("/reset-whats-new")
async def reset_whats_new_for_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Reset the 'has_seen_whats_new' flag to False for all users.
    This will make all users see the "What's New" message again.
    
    Only accessible by CEO, COO, and HR Manager roles.
    """
    # Check if user has admin privileges
    if current_user.role not in [UserRole.ceo, UserRole.coo, UserRole.hr_manager, UserRole.department_head]:
        raise HTTPException(
            status_code=403,
            detail="Only CEO, COO, and HR Manager can reset What's New status"
        )
    
    try:
        # Count users before update
        count_query = await db.execute(
            select(User).where(User.is_active == True)
        )
        total_users = len(count_query.scalars().all())
        
        # Update all active users
        await db.execute(
            update(User)
            .where(User.is_active == True)
            .values(has_seen_whats_new=False)
        )
        
        await db.commit()
        
        return {
            "message": "Successfully reset What's New status for all users",
            "users_updated": total_users,
            "reset_by": f"{current_user.first_name} {current_user.last_name}",
            "reset_by_email": current_user.email
        }
        
    except Exception as e:
        await db.rollback()
        print(f"Error resetting What's New status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset What's New status: {str(e)}"
        )


@router.post("/reset-ceo-message")
async def reset_ceo_message_for_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Reset the 'has_read_ceo_message' flag to False for all users.
    This will make all users see the CEO message again.
    
    Only accessible by CEO and COO roles.
    """
    # Check if user has admin privileges
    if current_user.role not in [UserRole.ceo, UserRole.coo, UserRole.department_head]:
        raise HTTPException(
            status_code=403,
            detail="Only CEO and COO can reset CEO message status"
        )
    
    try:
        # Count users before update
        count_query = await db.execute(
            select(User).where(User.is_active == True)
        )
        total_users = len(count_query.scalars().all())
        
        # Update all active users
        await db.execute(
            update(User)
            .where(User.is_active == True)
            .values(has_read_ceo_message=False)
        )
        
        await db.commit()
        
        return {
            "message": "Successfully reset CEO message status for all users",
            "users_updated": total_users,
            "reset_by": f"{current_user.first_name} {current_user.last_name}",
            "reset_by_email": current_user.email
        }
        
    except Exception as e:
        await db.rollback()
        print(f"Error resetting CEO message status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset CEO message status: {str(e)}"
        )


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get system-wide statistics for admin dashboard.
    
    Only accessible by CEO, COO, and HR Manager roles.
    """
    if current_user.role not in [UserRole.ceo, UserRole.coo, UserRole.hr_manager]:
        raise HTTPException(
            status_code=403,
            detail="Only CEO, COO, and HR Manager can access admin stats"
        )
    
    try:
        # Count active users
        active_users_query = await db.execute(
            select(User).where(User.is_active == True)
        )
        total_active_users = len(active_users_query.scalars().all())
        
        # Count users who have seen What's New
        seen_whats_new_query = await db.execute(
            select(User).where(
                User.is_active == True,
                User.has_seen_whats_new == True
            )
        )
        users_seen_whats_new = len(seen_whats_new_query.scalars().all())
        
        # Count users who have read CEO message
        read_ceo_message_query = await db.execute(
            select(User).where(
                User.is_active == True,
                User.has_read_ceo_message == True
            )
        )
        users_read_ceo_message = len(read_ceo_message_query.scalars().all())
        
        # Calculate percentages
        whats_new_percentage = (users_seen_whats_new / total_active_users * 100) if total_active_users > 0 else 0
        ceo_message_percentage = (users_read_ceo_message / total_active_users * 100) if total_active_users > 0 else 0
        
        return {
            "total_active_users": total_active_users,
            "whats_new_stats": {
                "seen": users_seen_whats_new,
                "not_seen": total_active_users - users_seen_whats_new,
                "percentage_seen": round(whats_new_percentage, 1)
            },
            "ceo_message_stats": {
                "read": users_read_ceo_message,
                "not_read": total_active_users - users_read_ceo_message,
                "percentage_read": round(ceo_message_percentage, 1)
            }
        }
        
    except Exception as e:
        print(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch admin stats: {str(e)}"
        )