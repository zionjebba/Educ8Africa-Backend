# app/api/v1/endpoints/uploads.py

import logging
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.team import Team, TeamMember
from app.models.user import User
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])
from typing import Optional

@router.put("/profile/update")
async def update_user_profile(
    phone: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    booking_link: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Update user profile information
    All fields are optional - only provided fields will be updated
    """
    try:        
        if linkedin_url is not None:
            # More robust LinkedIn URL validation
            linkedin_url = linkedin_url.strip()
            
            if not linkedin_url:
                raise HTTPException(
                    status_code=400,
                    detail="LinkedIn URL cannot be empty"
                )
            
            # Check for proper LinkedIn URL format
            if not ("linkedin.com/in/" in linkedin_url or "www.linkedin.com/in/" in linkedin_url):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid LinkedIn URL format. Must be a valid LinkedIn profile URL (e.g., https://linkedin.com/in/username)"
                )
            
            # Ensure it starts with http:// or https://
            if not linkedin_url.startswith(('http://', 'https://')):
                raise HTTPException(
                    status_code=400,
                    detail="LinkedIn URL must start with http:// or https://"
                )
        
        # Validate skills JSON if provided
        if skills is not None:
            try:
                import json
                json.loads(skills)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Skills must be a valid JSON string"
                )
        
        if phone is not None:
            current_user.phone = phone
            
        if location is not None:
            current_user.location = location
            
        if skills is not None:
            current_user.skills = skills
                
        if linkedin_url is not None:
            current_user.linkedin_url = linkedin_url
            
        if booking_link is not None:
            current_user.booking_link = booking_link
        
        await db.commit()
        await db.refresh(current_user)
                
        return {
            "message": "Profile updated successfully",
            "user": {
                "user_id": str(current_user.user_id),
                "phone": current_user.phone,
                "location": current_user.location,
                "skills": current_user.skills,
                "linkedin_url": current_user.linkedin_url,
                "booking_link": current_user.booking_link,
                "avatar": current_user.avatar,
            }
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as ie:
        await db.rollback()
        # Parse the constraint violation to provide helpful error messages
        error_msg = str(ie.orig).lower()
        
        if "check_linkedin_url_format" in error_msg or "linkedin" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Invalid LinkedIn URL format. Please provide a valid LinkedIn profile URL (e.g., https://linkedin.com/in/username)"
            )
        elif "unique" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="This value is already in use by another user"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data provided. Please check your input and try again."
            )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update profile. Please try again later."
        )
    
@router.get("/my-team")
async def get_my_team(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get the team that the current user leads or is a member of."""
    try:
        if current_user.role.value in ['team_lead', 'department_head']:
            team_query = await db.execute(
                select(Team).where(Team.team_lead_id == current_user.user_id)
            )
            team = team_query.scalar_one_or_none()
            
            if team:
                return {
                    "team_id": team.team_id,
                    "team_name": team.name,
                    "is_lead": True,
                }
        
        membership_query = await db.execute(
            select(TeamMember)
            .options(joinedload(TeamMember.team))
            .where(TeamMember.user_id == current_user.user_id)
        )
        membership = membership_query.scalar_one_or_none()
        
        if membership:
            return {
                "team_id": membership.team.team_id,
                "team_name": membership.team.name,
                "is_lead": False,
            }
        
        raise HTTPException(status_code=404, detail="User is not part of any team")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team: {str(e)}")
    
@router.get("/all")
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get all active users in the system with their basic information."""
    try:
        logger.info(f"Fetching all users - requested by: {current_user.user_id}")
        
        users_query = await db.execute(
            select(User)
            .options(joinedload(User.department))
            .where(User.is_active == True)
            .order_by(User.first_name, User.last_name)
        )
        users = users_query.scalars().unique().all()
        
        # Format user data
        users_data = []
        for user in users:
            users_data.append({
                "user_id": str(user.user_id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "avatar": user.avatar or f"https://ui-avatars.com/api/?name={user.first_name}+{user.last_name}",
                "role": user.role.value if user.role else None,
                "department": user.department.name if user.department else None,
                "department_id": user.department_id,
            })
        
        logger.info(f"Successfully fetched {len(users_data)} users")
        
        return {
            "users": users_data,
            "total": len(users_data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch users: {str(e)}"
        )