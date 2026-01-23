"""Updated onboarding endpoints for Educ8Africa - 4 questions only."""

from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.constants.constants import AVAILABLE_ROLES, MISSION_VISSION_CARDS, UserRole
from app.core.database import aget_db
from app.models.onboarding import OnboardingResponse
from app.models.team import Team, TeamMember
from app.models.user import User
from app.models.department import Department
from app.core.security import get_current_user
from app.utils.onboarding.calculate_onboarding_score import calculate_onboarding_score
from app.utils.uploads.val_upload_avatar import validate_and_upload_avatar

router = APIRouter(
    prefix="/onboarding",
    tags=["onboarding"]
)

CORRECT_MISSION_VISION = "mission_card_1"


@router.get("/config")
async def get_onboarding_config(db: AsyncSession = Depends(aget_db)):
    """
    Get configuration for onboarding UI
    Returns available options for dropdowns, including teams and departments
    """
    result = await db.execute(
        select(Team, Department)
        .join(Department, Team.department_id == Department.department_id)
        .order_by(Department.name, Team.name)
    )
    teams_with_dept = result.all()
    
    teams_list = []
    for team, department in teams_with_dept:
        teams_list.append({
            "team_id": team.team_id,
            "team_name": team.name,
            "team_description": team.description,
            "department_id": department.department_id,
            "department_name": department.name,
            "department_description": department.description
        })
    
    return {
        "available_roles": AVAILABLE_ROLES,
        "mission_vision_cards": MISSION_VISSION_CARDS,
        "teams": teams_list
    }


@router.post("/submit")
async def submit_onboarding(
    mission_vision_choice: str = Form(...),
    selected_role: str = Form(...),
    selected_team_id: str = Form(...),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Submit complete onboarding form
    Handles avatar upload to S3, team assignment, and all onboarding data
    """
    if current_user.onboarding_completed:
        raise HTTPException(
            status_code=400,
            detail="Onboarding already completed"
        )
    
    allowed_roles = ["employee", "intern", "nsp", "admin"]
    if selected_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
        )
    
    team_result = await db.execute(
        select(Team).where(Team.team_id == selected_team_id)
    )
    selected_team = team_result.scalar_one_or_none()
    
    if not selected_team:
        raise HTTPException(
            status_code=400,
            detail="Invalid team selection"
        )
    
    avatar_url = current_user.avatar
    if avatar:
        username = current_user.first_name or current_user.email or f"user_{current_user.user_id}"
        avatar_url = await validate_and_upload_avatar(avatar, username)
    
    mission_correct = mission_vision_choice == CORRECT_MISSION_VISION
    
    # Only mission/vision counts for scoring now
    total_score, points_earned = calculate_onboarding_score(False, mission_correct)
    
    existing_response = await db.execute(
        select(OnboardingResponse).where(
            OnboardingResponse.user_id == current_user.user_id
        )
    )
    onboarding_response = existing_response.scalar_one_or_none()
    
    if onboarding_response:
        onboarding_response.mission_vision_choice = mission_vision_choice
        onboarding_response.mission_vision_correct = mission_correct
        onboarding_response.total_score = total_score
        onboarding_response.points_earned = points_earned
        onboarding_response.completed_at = datetime.utcnow()
    else:
        onboarding_response = OnboardingResponse(
            response_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            mission_vision_choice=mission_vision_choice,
            mission_vision_correct=mission_correct,
            total_score=total_score,
            points_earned=points_earned,
            completed_at=datetime.utcnow()
        )
        db.add(onboarding_response)
    
    current_user.onboarding_completed = True
    current_user.onboarding_completed_at = datetime.utcnow()
    current_user.onboarding_score = total_score
    current_user.onboarding_points = points_earned
    current_user.points += points_earned
    current_user.avatar = avatar_url
    current_user.role = UserRole(selected_role)
    
    current_user.department_id = selected_team.department_id
    
    existing_membership = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.user_id,
            TeamMember.team_id == selected_team_id
        )
    )
    membership = existing_membership.scalar_one_or_none()
    
    if not membership:
        team_membership = TeamMember(
            membership_id=str(uuid.uuid4()),
            team_id=selected_team_id,
            user_id=current_user.user_id,
            role_in_team=selected_role.replace("_", " ").title(),
            joined_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(team_membership)
    
    try:
        await db.commit()
        await db.refresh(current_user)
        
        dept_result = await db.execute(
            select(Department).where(Department.department_id == selected_team.department_id)
        )
        department = dept_result.scalar_one_or_none()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save onboarding data: {str(e)}"
        )
    
    return {
        "message": "Onboarding completed successfully!",
        "score": total_score,
        "points_earned": points_earned,
        "total_points": current_user.points,
        "mission_correct": mission_correct,
        "avatar_url": avatar_url,
        "role": selected_role,
        "team_name": selected_team.name,
        "department_name": department.name if department else "Unknown",
        "department_id": selected_team.department_id
    }


@router.post("/skip")
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Allow user to skip onboarding (no points awarded)
    Automatically assigns them to Research Team in R&D Department
    """
    if current_user.onboarding_completed:
        raise HTTPException(
            status_code=400,
            detail="Onboarding already completed"
        )
    
    research_team_result = await db.execute(
        select(Team).where(Team.name == "Research Team")
    )
    research_team = research_team_result.scalar_one_or_none()
    
    if not research_team:
        raise HTTPException(
            status_code=500,
            detail="Default team (Research Team) not found. Please contact administrator."
        )
    
    dept_result = await db.execute(
        select(Department).where(Department.department_id == research_team.department_id)
    )
    department = dept_result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(
            status_code=500,
            detail="Department not found for Research Team. Please contact administrator."
        )
    
    current_user.onboarding_completed = True
    current_user.onboarding_skipped = True
    current_user.onboarding_completed_at = datetime.utcnow()
    current_user.onboarding_score = 0
    current_user.onboarding_points = 0
    current_user.role = UserRole.employee
    current_user.department_id = research_team.department_id
    current_user.department = department.name
    
    existing_membership = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.user_id,
            TeamMember.team_id == research_team.team_id
        )
    )
    membership = existing_membership.scalar_one_or_none()
    
    if not membership:
        team_membership = TeamMember(
            membership_id=str(uuid.uuid4()),
            team_id=research_team.team_id,
            user_id=current_user.user_id,
            role_in_team="Employee",
            joined_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(team_membership)
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to skip onboarding: {str(e)}"
        )
    
    return {
        "message": "Onboarding skipped - You have been assigned to Research Team",
        "points_earned": 0,
        "team_name": research_team.name,
        "department_name": department.name
    }

@router.get("/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Check onboarding status for current user
    """
    if current_user.onboarding_completed:
        result = await db.execute(
            select(OnboardingResponse).where(
                OnboardingResponse.user_id == current_user.user_id
            )
        )
        response = result.scalar_one_or_none()
        
        team_info = None
        if current_user.department_id:
            dept_result = await db.execute(
                select(Department).where(Department.department_id == current_user.department_id)
            )
            department = dept_result.scalar_one_or_none()
            
            teams_result = await db.execute(
                select(Team, TeamMember)
                .join(TeamMember, Team.team_id == TeamMember.team_id)
                .where(TeamMember.user_id == current_user.user_id)
            )
            teams = teams_result.all()
            
            team_info = {
                "department_name": department.name if department else None,
                "department_id": current_user.department_id,
                "teams": [
                    {
                        "team_id": team.team_id,
                        "team_name": team.name,
                        "role_in_team": membership.role_in_team
                    }
                    for team, membership in teams
                ]
            }
        
        return {
            "completed": True,
            "skipped": current_user.onboarding_skipped,
            "score": current_user.onboarding_score,
            "points_earned": current_user.onboarding_points,
            "completed_at": current_user.onboarding_completed_at,
            "team_info": team_info,
            "details": {
                "mission_correct": response.mission_vision_correct if response else None,
            } if response else None
        }
    
    return {
        "completed": False,
        "skipped": False
    }