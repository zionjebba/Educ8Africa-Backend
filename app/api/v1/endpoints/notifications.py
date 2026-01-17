

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime
from typing import List

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.notifications import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get notifications for the current user."""
    
    query = select(Notification).where(Notification.user_id == current_user.user_id)
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # Get unread count
    unread_query = await db.execute(
        select(func.count(Notification.notification_id))
        .where(
            and_(
                Notification.user_id == current_user.user_id,
                Notification.is_read == False
            )
        )
    )
    unread_count = unread_query.scalar()
    
    return {
        "notifications": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "action_url": n.action_url,
                "action_label": n.action_label,
                "reference_id": n.reference_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ],
        "unread_count": unread_count
    }


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Mark a notification as read."""
    
    query = await db.execute(
        select(Notification).where(
            and_(
                Notification.notification_id == notification_id,
                Notification.user_id == current_user.user_id
            )
        )
    )
    notification = query.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True}


@router.post("/read-all")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Mark all notifications as read for the current user."""
    
    query = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == current_user.user_id,
                Notification.is_read == False
            )
        )
    )
    notifications = query.scalars().all()
    
    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "marked_count": len(notifications)
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Delete a notification."""
    
    query = await db.execute(
        select(Notification).where(
            and_(
                Notification.notification_id == notification_id,
                Notification.user_id == current_user.user_id
            )
        )
    )
    notification = query.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await db.delete(notification)
    await db.commit()
    
    return {"success": True}
