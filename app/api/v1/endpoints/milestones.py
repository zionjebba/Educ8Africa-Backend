from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Optional
import uuid
from sqlalchemy.orm import joinedload

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.milestones import Milestone
from app.models.team import Team
from app.models.user import User

router = APIRouter(prefix="/milestones", tags=["milestones"])

class MilestoneCreate(BaseModel):
    title: str
    description: Optional[str] = None
    team_id: str

class MilestoneResponse(BaseModel):
    milestone_id: str
    title: str
    description: Optional[str]
    week_start_date: datetime
    week_end_date: datetime
    total_tasks: int
    completed_tasks: int
    is_completed: bool
    team_name: str

def get_week_range(date: datetime = None):
    """Get the Monday-Sunday range for a given date."""
    if date is None:
        date = datetime.utcnow()
    
    start_of_week = date - timedelta(days=date.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return start_of_week, end_of_week

@router.get("/current-week-status")
async def get_current_week_milestone_status(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Check if current week's milestone is already set for the team.
    Returns milestone if exists, or null with can_create flag.
    """
    try:
        team_query = await db.execute(
            select(Team).where(Team.team_id == team_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        if team.team_lead_id != current_user.user_id:
            if not team.department or team.department.head_id != current_user.user_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Only team leads or department heads can access this"
                )
        
        week_start, week_end = get_week_range()
        
        milestone_query = await db.execute(
            select(Milestone)
            .where(
                and_(
                    Milestone.team_id == team_id,
                    Milestone.week_start_date == week_start
                )
            )
        )
        milestone = milestone_query.scalar_one_or_none()
        
        if milestone:
            return {
                "has_milestone": True,
                "can_create": False,
                "milestone": {
                    "milestone_id": milestone.milestone_id,
                    "title": milestone.title,
                    "description": milestone.description,
                    "week_start_date": milestone.week_start_date,
                    "week_end_date": milestone.week_end_date,
                    "total_tasks": milestone.total_tasks,
                    "completed_tasks": milestone.completed_tasks,
                    "is_completed": milestone.is_completed,
                }
            }
        
        return {
            "has_milestone": False,
            "can_create": True,
            "week_start_date": week_start,
            "week_end_date": week_end,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking milestone status: {str(e)}")

@router.post("/create")
async def create_milestone(
    milestone_data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Create a new weekly milestone for a team.
    Only team leads can create milestones for their teams.
    """
    try:
        team_query = await db.execute(
            select(Team)
            .options(joinedload(Team.department))
            .where(Team.team_id == milestone_data.team_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        if team.team_lead_id != current_user.user_id:
            raise HTTPException(
                status_code=403, 
                detail="Only the team lead can create milestones"
            )
        
        week_start, week_end = get_week_range()
        
        existing_query = await db.execute(
            select(Milestone)
            .where(
                and_(
                    Milestone.team_id == milestone_data.team_id,
                    Milestone.week_start_date == week_start
                )
            )
        )
        existing = existing_query.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Milestone already exists for this week"
            )
        
        milestone = Milestone(
            milestone_id=str(uuid.uuid4()),
            team_id=milestone_data.team_id,
            title=milestone_data.title,
            description=milestone_data.description,
            week_start_date=week_start,
            week_end_date=week_end,
            created_by=current_user.user_id,
        )
        
        db.add(milestone)
        await db.commit()
        await db.refresh(milestone)
        
        return {
            "message": "Milestone created successfully",
            "milestone": {
                "milestone_id": milestone.milestone_id,
                "title": milestone.title,
                "description": milestone.description,
                "week_start_date": milestone.week_start_date,
                "week_end_date": milestone.week_end_date,
                "team_name": team.name,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating milestone: {str(e)}")

@router.get("/team/{team_id}")
async def get_team_milestones(
    team_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get all milestones for a team, ordered by week."""
    try:
        query = await db.execute(
            select(Milestone)
            .options(joinedload(Milestone.team))
            .where(Milestone.team_id == team_id)
            .order_by(Milestone.week_start_date.desc())
            .limit(limit)
        )
        milestones = query.scalars().all()
        
        return {
            "milestones": [
                {
                    "milestone_id": m.milestone_id,
                    "title": m.title,
                    "description": m.description,
                    "week_start_date": m.week_start_date,
                    "week_end_date": m.week_end_date,
                    "total_tasks": m.total_tasks,
                    "completed_tasks": m.completed_tasks,
                    "is_completed": m.is_completed,
                    "team_name": m.team.name,
                }
                for m in milestones
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching milestones: {str(e)}")