"""Enhanced Recognition System for Dashboard and Performance Engine"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.team import Team, TeamMember
from app.models.department import Department
from app.constants.constants import TaskStatus

router = APIRouter(
    prefix="/recognition",
    tags=["recognition"]
)


def calculate_completion_and_ontime_rate(tasks_list):
    """
    Calculate completion rate and on-time delivery rate.
    Returns (completion_rate, on_time_rate, total_score)
    """
    if not tasks_list:
        return 0.0, 0.0, 0.0
    
    total_tasks = len(tasks_list)
    completed_tasks = [t for t in tasks_list if t.status == TaskStatus.completed]
    completed_count = len(completed_tasks)
    
    completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0.0
    
    on_time_count = 0
    early_count = 0
    total_early_minutes = 0
    
    for t in completed_tasks:
        if t.report and t.report.submitted_at and t.due_date:
            submitted_at = t.report.submitted_at
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
            
            due_date = t.due_date
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            if submitted_at <= due_date:
                on_time_count += 1
                
                # Calculate how early (in minutes)
                time_diff = (due_date - submitted_at).total_seconds() / 60
                if time_diff > 0:
                    early_count += 1
                    total_early_minutes += time_diff
    
    on_time_rate = (on_time_count / completed_count * 100) if completed_count > 0 else 0.0
    
    # Average early minutes (for timeliness scoring)
    avg_early_minutes = total_early_minutes / early_count if early_count > 0 else 0
    
    # Combined score (60% completion, 40% on-time)
    total_score = (completion_rate * 0.6 + on_time_rate * 0.4)
    
    return completion_rate, on_time_rate, total_score, avg_early_minutes


async def get_most_timely_person(db: AsyncSession, today: datetime) -> Optional[Dict]:
    """Get the person with the highest rate of early/on-time completions."""
    
    # Get all active users
    users_query = await db.execute(
        select(User)
        .where(User.is_active == True)
        .options(joinedload(User.department))
    )
    users = users_query.scalars().unique().all()
    
    best_user = None
    best_score = -1
    
    for user in users:
        # Get completed tasks in the last 30 days
        period_start = today - timedelta(days=30)
        
        tasks_query = await db.execute(
            select(Task)
            .options(selectinload(Task.report))
            .where(
                Task.user_id == user.user_id,
                Task.status == TaskStatus.completed,
                Task.completed_at >= period_start
            )
        )
        tasks = tasks_query.scalars().all()
        
        if not tasks or len(tasks) < 3:  # Minimum 3 completed tasks
            continue
        
        on_time_count = 0
        early_count = 0
        total_early_minutes = 0
        
        for task in tasks:
            if task.report and task.report.submitted_at and task.due_date:
                submitted_at = task.report.submitted_at
                if submitted_at.tzinfo is None:
                    submitted_at = submitted_at.replace(tzinfo=timezone.utc)
                
                due_date = task.due_date
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                if submitted_at <= due_date:
                    on_time_count += 1
                    
                    time_diff = (due_date - submitted_at).total_seconds() / 60
                    if time_diff > 0:
                        early_count += 1
                        total_early_minutes += time_diff
        
        # Calculate timeliness score
        on_time_rate = (on_time_count / len(tasks)) * 100
        avg_early_minutes = total_early_minutes / early_count if early_count > 0 else 0
        
        # Score: 70% on-time rate + 30% average early time (normalized)
        # Normalize early minutes: 30+ minutes early = max points
        early_score = min(avg_early_minutes / 30, 1.0) * 100
        timeliness_score = (on_time_rate * 0.7) + (early_score * 0.3)
        
        if timeliness_score > best_score:
            best_score = timeliness_score
            best_user = {
                "user": user,
                "on_time_rate": on_time_rate,
                "avg_early_minutes": avg_early_minutes,
                "completed_count": len(tasks)
            }
    
    return best_user


async def get_top_performing_teams(db: AsyncSession, today: datetime, limit: int = None) -> List[Dict]:
    """Get top performing teams based on completion and on-time rates."""
    
    teams_query = await db.execute(
        select(Team)
        .options(
            joinedload(Team.department),
            joinedload(Team.team_lead)
        )
    )
    teams = teams_query.scalars().unique().all()
    
    team_scores = []
    
    for team in teams:
        # Get all team members
        members_query = await db.execute(
            select(TeamMember.user_id)
            .where(TeamMember.team_id == team.team_id)
        )
        member_ids = [row[0] for row in members_query.all()]
        
        if not member_ids:
            continue
        
        # Get all team tasks
        tasks_query = await db.execute(
            select(Task)
            .options(selectinload(Task.report))
            .where(Task.user_id.in_(member_ids))
        )
        tasks = tasks_query.scalars().all()
        
        if not tasks:
            continue
        
        completion_rate, on_time_rate, total_score, _ = calculate_completion_and_ontime_rate(tasks)
        
        team_scores.append({
            "team": team,
            "completion_rate": completion_rate,
            "on_time_rate": on_time_rate,
            "total_score": total_score,
            "total_tasks": len(tasks)
        })
    
    # Sort by total score
    team_scores.sort(key=lambda x: x['total_score'], reverse=True)
    
    if limit:
        team_scores = team_scores[:limit]
    
    return team_scores


async def get_top_performing_departments(db: AsyncSession, today: datetime, limit: int = None) -> List[Dict]:
    """Get top performing departments."""
    
    depts_query = await db.execute(
        select(Department)
        .options(joinedload(Department.head))
    )
    departments = depts_query.scalars().unique().all()
    
    dept_scores = []
    
    for dept in departments:
        # Get all teams in department
        teams_query = await db.execute(
            select(Team.team_id)
            .where(Team.department_id == dept.department_id)
        )
        team_ids = [row[0] for row in teams_query.all()]
        
        if not team_ids:
            continue
        
        # Get all members in these teams
        members_query = await db.execute(
            select(TeamMember.user_id)
            .where(TeamMember.team_id.in_(team_ids))
        )
        member_ids = [row[0] for row in members_query.all()]
        
        if not member_ids:
            continue
        
        # Get all department tasks
        tasks_query = await db.execute(
            select(Task)
            .options(selectinload(Task.report))
            .where(Task.user_id.in_(member_ids))
        )
        tasks = tasks_query.scalars().all()
        
        if not tasks:
            continue
        
        completion_rate, on_time_rate, total_score, _ = calculate_completion_and_ontime_rate(tasks)
        
        dept_scores.append({
            "department": dept,
            "completion_rate": completion_rate,
            "on_time_rate": on_time_rate,
            "total_score": total_score,
            "total_tasks": len(tasks)
        })
    
    dept_scores.sort(key=lambda x: x['total_score'], reverse=True)
    
    if limit:
        dept_scores = dept_scores[:limit]
    
    return dept_scores


async def get_top_team_members_per_team(db: AsyncSession, today: datetime) -> List[Dict]:
    """Get top performing member in each team."""
    
    teams_query = await db.execute(
        select(Team)
        .options(joinedload(Team.department))
    )
    teams = teams_query.scalars().unique().all()
    
    top_members = []
    
    for team in teams:
        members_query = await db.execute(
            select(TeamMember)
            .options(joinedload(TeamMember.user).joinedload(User.department))
            .where(TeamMember.team_id == team.team_id)
        )
        members = members_query.scalars().unique().all()
        
        if not members:
            continue
        
        best_member = None
        best_score = -1
        
        for member in members:
            user = member.user
            
            tasks_query = await db.execute(
                select(Task)
                .options(selectinload(Task.report))
                .where(Task.user_id == user.user_id)
            )
            tasks = tasks_query.scalars().all()
            
            if not tasks:
                continue
            
            _, _, total_score, _ = calculate_completion_and_ontime_rate(tasks)
            
            if total_score > best_score:
                best_score = total_score
                best_member = {
                    "user": user,
                    "team": team,
                    "score": total_score,
                    "total_tasks": len(tasks)
                }
        
        if best_member:
            top_members.append(best_member)
    
    return top_members


async def get_top_department_members_per_department(db: AsyncSession, today: datetime) -> List[Dict]:
    """Get top performing member in each department."""
    
    depts_query = await db.execute(
        select(Department)
    )
    departments = depts_query.scalars().all()
    
    top_members = []
    
    for dept in departments:
        # Get all teams in department
        teams_query = await db.execute(
            select(Team.team_id)
            .where(Team.department_id == dept.department_id)
        )
        team_ids = [row[0] for row in teams_query.all()]
        
        if not team_ids:
            continue
        
        # Get all members
        members_query = await db.execute(
            select(TeamMember)
            .options(joinedload(TeamMember.user).joinedload(User.department))
            .where(TeamMember.team_id.in_(team_ids))
        )
        members = members_query.scalars().unique().all()
        
        if not members:
            continue
        
        best_member = None
        best_score = -1
        
        for member in members:
            user = member.user
            
            tasks_query = await db.execute(
                select(Task)
                .options(selectinload(Task.report))
                .where(Task.user_id == user.user_id)
            )
            tasks = tasks_query.scalars().all()
            
            if not tasks:
                continue
            
            _, _, total_score, _ = calculate_completion_and_ontime_rate(tasks)
            
            if total_score > best_score:
                best_score = total_score
                best_member = {
                    "user": user,
                    "department": dept,
                    "score": total_score,
                    "total_tasks": len(tasks)
                }
        
        if best_member:
            top_members.append(best_member)
    
    return top_members


async def get_most_cultured_person(db: AsyncSession) -> Optional[Dict]:
    """Get person with highest culture points."""
    
    user_query = await db.execute(
        select(User)
        .where(User.is_active == True)
        .options(joinedload(User.department))
        .order_by(User.culture_points.desc())
        .limit(1)
    )
    user = user_query.scalar_one_or_none()
    
    if user and user.culture_points > 0:
        return {
            "user": user,
            "culture_points": user.culture_points
        }
    
    return None


@router.get("/all-recognitions")
async def get_all_recognitions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all recognition titles with winners.
    Returns comprehensive recognition data for performance engine.
    """
    today = datetime.utcnow()
    recognitions = []
    
    # 1. Top Performing Team
    top_teams = await get_top_performing_teams(db, today, limit=1)
    if top_teams:
        team_data = top_teams[0]
        recognitions.append({
            "id": "top_performing_team",
            "title": "Top Performing Team",
            "description": "Team with highest completion rate and on-time delivery",
            "winner": {
                "type": "team",
                "name": team_data["team"].name,
                "department": team_data["team"].department.name if team_data["team"].department else None,
                "completion_rate": f"{team_data['completion_rate']:.1f}%",
                "on_time_rate": f"{team_data['on_time_rate']:.1f}%",
                "score": f"{team_data['total_score']:.1f}",
                "total_tasks": team_data['total_tasks']
            }
        })
    
    # 2. Top Performing Department
    top_depts = await get_top_performing_departments(db, today, limit=1)
    if top_depts:
        dept_data = top_depts[0]
        recognitions.append({
            "id": "top_performing_department",
            "title": "Top Performing Department",
            "description": "Department with highest completion rate and on-time delivery",
            "winner": {
                "type": "department",
                "name": dept_data["department"].name,
                "head": f"{dept_data['department'].head.first_name} {dept_data['department'].head.last_name}" if dept_data['department'].head else None,
                "completion_rate": f"{dept_data['completion_rate']:.1f}%",
                "on_time_rate": f"{dept_data['on_time_rate']:.1f}%",
                "score": f"{dept_data['total_score']:.1f}",
                "total_tasks": dept_data['total_tasks']
            }
        })
    
    # 3. Top Performing Team Lead
    if top_teams:
        team_data = top_teams[0]
        if team_data["team"].team_lead:
            recognitions.append({
                "id": "top_performing_team_lead",
                "title": "Top Performing Team Lead",
                "description": "Team lead of the top performing team",
                "winner": {
                    "type": "user",
                    "name": f"{team_data['team'].team_lead.first_name} {team_data['team'].team_lead.last_name}",
                    "avatar": team_data['team'].team_lead.avatar,
                    "team": team_data["team"].name,
                    "department": team_data["team"].department.name if team_data["team"].department else None,
                    "team_score": f"{team_data['total_score']:.1f}"
                }
            })
    
    # 4. Top Performing Department Head
    if top_depts:
        dept_data = top_depts[0]
        if dept_data["department"].head:
            recognitions.append({
                "id": "top_performing_department_head",
                "title": "Top Performing Department Head",
                "description": "Head of the top performing department",
                "winner": {
                    "type": "user",
                    "name": f"{dept_data['department'].head.first_name} {dept_data['department'].head.last_name}",
                    "avatar": dept_data['department'].head.avatar,
                    "department": dept_data["department"].name,
                    "department_score": f"{dept_data['total_score']:.1f}"
                }
            })
    
    # 5. Most Timely Person
    most_timely = await get_most_timely_person(db, today)
    if most_timely:
        recognitions.append({
            "id": "most_timely",
            "title": "Most Timely",
            "description": "Individual with highest rate of early/on-time task completion",
            "winner": {
                "type": "user",
                "name": f"{most_timely['user'].first_name} {most_timely['user'].last_name}",
                "avatar": most_timely['user'].avatar,
                "department": most_timely['user'].department.name if most_timely['user'].department else None,
                "on_time_rate": f"{most_timely['on_time_rate']:.1f}%",
                "avg_early_minutes": f"{most_timely['avg_early_minutes']:.0f} min",
                "completed_count": most_timely['completed_count']
            }
        })
    
    # 6. Most Cultured
    most_cultured = await get_most_cultured_person(db)
    if most_cultured:
        recognitions.append({
            "id": "most_cultured",
            "title": "Most Cultured",
            "description": "Individual with highest culture points",
            "winner": {
                "type": "user",
                "name": f"{most_cultured['user'].first_name} {most_cultured['user'].last_name}",
                "avatar": most_cultured['user'].avatar,
                "department": most_cultured['user'].department.name if most_cultured['user'].department else None,
                "culture_points": most_cultured['culture_points']
            }
        })
    
    # 7. Top Team Members (grouped by team)
    top_team_members = await get_top_team_members_per_team(db, today)
    if top_team_members:
        team_members_data = []
        for member_data in top_team_members[:5]:  # Limit to top 5 teams
            team_members_data.append({
                "name": f"{member_data['user'].first_name} {member_data['user'].last_name}",
                "avatar": member_data['user'].avatar,
                "team": member_data['team'].name,
                "department": member_data['team'].department.name if member_data['team'].department else None,
                "score": f"{member_data['score']:.1f}",
                "total_tasks": member_data['total_tasks']
            })
        
        if team_members_data:
            recognitions.append({
                "id": "top_team_members",
                "title": "Top Team Members",
                "description": "Best performing member in each team",
                "winners": team_members_data
            })
    
    # 8. Top Department Members (grouped by department)
    top_dept_members = await get_top_department_members_per_department(db, today)
    if top_dept_members:
        dept_members_data = []
        for member_data in top_dept_members:
            dept_members_data.append({
                "name": f"{member_data['user'].first_name} {member_data['user'].last_name}",
                "avatar": member_data['user'].avatar,
                "department": member_data['department'].name,
                "score": f"{member_data['score']:.1f}",
                "total_tasks": member_data['total_tasks']
            })
        
        if dept_members_data:
            recognitions.append({
                "id": "top_department_members",
                "title": "Top Department Members",
                "description": "Best performing member in each department",
                "winners": dept_members_data
            })
    
    return {
        "recognitions": recognitions,
        "total_count": len(recognitions),
        "generated_at": today.isoformat()
    }


@router.get("/today")
async def get_todays_recognition(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get top 3 recognition awards for today (for dashboard).
    Returns: Most Timely, Most Cultured, and Top Performing Team
    """
    today = datetime.utcnow()
    recognitions = []
    
    # 1. Most Timely Person
    most_timely = await get_most_timely_person(db, today)
    if most_timely:
        recognitions.append({
            "id": 1,
            "name": f"{most_timely['user'].first_name} {most_timely['user'].last_name}",
            "title": "Most Timely",
            "image": most_timely['user'].avatar,
            "type": "avatar",
            "department": most_timely['user'].department.name if most_timely['user'].department else None,
            "on_time_rate": f"{most_timely['on_time_rate']:.1f}%",
            "avg_early": f"{most_timely['avg_early_minutes']:.0f} min early"
        })
    
    # 2. Most Cultured
    most_cultured = await get_most_cultured_person(db)
    if most_cultured:
        recognitions.append({
            "id": 2,
            "name": f"{most_cultured['user'].first_name} {most_cultured['user'].last_name}",
            "title": "Most Cultured",
            "image": most_cultured['user'].avatar,
            "type": "avatar",
            "department": most_cultured['user'].department.name if most_cultured['user'].department else None,
            "culture_points": most_cultured['culture_points']
        })
    
    # 3. Top Performing Team
    top_teams = await get_top_performing_teams(db, today, limit=1)
    if top_teams:
        team_data = top_teams[0]
        recognitions.append({
            "id": 3,
            "name": team_data["team"].name,
            "title": "Top Performing Team",
            "type": "group",
            "department": team_data["team"].department.name if team_data["team"].department else None,
            "score": f"{team_data['total_score']:.1f}/100"
        })
    
    return {
        "recognitions": recognitions
    }