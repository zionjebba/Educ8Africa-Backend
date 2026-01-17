"""Dashboard router for Educ8Africa system - Extended with role-specific endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_, or_
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
    prefix="/dashboard",
    tags=["dashboard"]
)


def calculate_performance_score(tasks_list):
    """
    Calculate performance score based on completion rate and on-time delivery.
    Returns a score out of 10.
    """
    if not tasks_list:
        return 0.0
    
    total_tasks = len(tasks_list)
    completed_tasks = [t for t in tasks_list if t.status == TaskStatus.completed]
    completed_count = len(completed_tasks)
    
    # Completion rate (60% weight)
    completion_rate = (completed_count / total_tasks) if total_tasks > 0 else 0
    
    # On-time delivery rate (40% weight)
    on_time_count = 0
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
    
    on_time_rate = (on_time_count / completed_count) if completed_count > 0 else 0
    
    performance_score = (completion_rate * 0.6 + on_time_rate * 0.4) * 10
    
    return performance_score


@router.get("/team-lead/stats")
async def get_team_lead_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    team_query = await db.execute(
        select(Team)
        .where(Team.team_lead_id == current_user.user_id)
    )
    team = team_query.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found for this team lead")
    
    members_query = await db.execute(
        select(func.count(TeamMember.membership_id))
        .where(TeamMember.team_id == team.team_id)
    )
    team_members_count = members_query.scalar() or 0
    
    team_member_ids_query = await db.execute(
        select(TeamMember.user_id)
        .where(TeamMember.team_id == team.team_id)
    )
    team_member_ids = [row[0] for row in team_member_ids_query.all()]
    
    if team_member_ids:
        tasks_query = await db.execute(
            select(Task)
            .options(selectinload(Task.report))
            .where(Task.user_id.in_(team_member_ids))
        )
        all_tasks = tasks_query.scalars().all()
        
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.completed])
        pending_tasks = len([t for t in all_tasks if t.status == TaskStatus.pending])
        in_progress_tasks = len([t for t in all_tasks if t.status == TaskStatus.in_progress])
        
        team_score = calculate_performance_score(all_tasks)
    else:
        total_tasks = 0
        completed_tasks = 0
        pending_tasks = 0
        in_progress_tasks = 0
        team_score = 0.0
    
    return {
        "team_members": team_members_count,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "team_score": f"{team_score:.1f}/10",
        "team_name": team.name
    }


@router.get("/team-lead/team-tasks-today")
async def get_team_tasks_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    team_query = await db.execute(
        select(Team)
        .where(Team.team_lead_id == current_user.user_id)
    )
    team = team_query.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found for this team lead")
    
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    members_query = await db.execute(
        select(TeamMember)
        .options(joinedload(TeamMember.user))
        .where(TeamMember.team_id == team.team_id)
    )
    members = members_query.scalars().unique().all()
    
    team_tasks = []
    
    for member in members:
        user = member.user
        
        tasks_query = await db.execute(
            select(Task)
            .where(
                and_(
                    Task.user_id == user.user_id,
                    or_(
                        and_(
                            Task.due_date >= datetime.combine(today, datetime.min.time()),
                            Task.due_date < datetime.combine(tomorrow, datetime.min.time())
                        ),
                        and_(
                            Task.due_date < datetime.combine(today, datetime.min.time()),
                            Task.status.not_in([TaskStatus.completed, TaskStatus.cancelled])
                        )
                    )
                )
            )
            .order_by(Task.due_date.asc())
        )
        tasks = tasks_query.scalars().all()
        
        team_tasks.append({
            "member_id": user.user_id,
            "member_name": f"{user.first_name} {user.last_name}",
            "member_avatar": user.avatar,
            "tasks": [
                {
                    "id": task.task_id,
                    "title": task.title,
                    "description": task.description,
                    "due_time": task.due_date.strftime("%I:%M %p"),
                    "due_date": task.due_date.isoformat(),
                    "status": task.status.value,
                    "category": task.category
                }
                for task in tasks
            ],
            "tasks_count": len(tasks)
        })
    
    return {
        "team_name": team.name,
        "team_tasks": team_tasks
    }


@router.get("/department-head/stats")
async def get_department_head_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    dept_query = await db.execute(
        select(Department)
        .where(Department.head_id == current_user.user_id)
    )
    department = dept_query.scalar_one_or_none()
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found for this department head")
    
    teams_query = await db.execute(
        select(func.count(Team.team_id))
        .where(Team.department_id == department.department_id)
    )
    teams_count = teams_query.scalar() or 0
    
    team_ids_query = await db.execute(
        select(Team.team_id)
        .where(Team.department_id == department.department_id)
    )
    team_ids = [row[0] for row in team_ids_query.all()]
    
    total_members = 0
    if team_ids:
        members_query = await db.execute(
            select(func.count(TeamMember.membership_id))
            .where(TeamMember.team_id.in_(team_ids))
        )
        total_members = members_query.scalar() or 0
    
    if team_ids:
        member_ids_query = await db.execute(
            select(TeamMember.user_id)
            .where(TeamMember.team_id.in_(team_ids))
        )
        member_ids = [row[0] for row in member_ids_query.all()]
        
        if member_ids:
            tasks_query = await db.execute(
                select(Task)
                .options(selectinload(Task.report))
                .where(Task.user_id.in_(member_ids))
            )
            all_tasks = tasks_query.scalars().all()
            
            total_tasks = len(all_tasks)
            completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.completed])
            pending_tasks = len([t for t in all_tasks if t.status == TaskStatus.pending])
            in_progress_tasks = len([t for t in all_tasks if t.status == TaskStatus.in_progress])
            
            dept_score = calculate_performance_score(all_tasks)
        else:
            total_tasks = completed_tasks = pending_tasks = in_progress_tasks = 0
            dept_score = 0.0
    else:
        total_tasks = completed_tasks = pending_tasks = in_progress_tasks = 0
        dept_score = 0.0
    
    return {
        "teams_count": teams_count,
        "total_members": total_members,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "department_score": f"{dept_score:.1f}/10",
        "department_name": department.name
    }


@router.get("/department-head/department-tasks-today")
async def get_department_tasks_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    dept_query = await db.execute(
        select(Department)
        .where(Department.head_id == current_user.user_id)
    )
    department = dept_query.scalar_one_or_none()
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found for this department head")
    
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    teams_query = await db.execute(
        select(Team)
        .where(Team.department_id == department.department_id)
    )
    teams = teams_query.scalars().all()
    
    department_tasks = []
    
    for team in teams:
        members_query = await db.execute(
            select(TeamMember)
            .options(joinedload(TeamMember.user))
            .where(TeamMember.team_id == team.team_id)
        )
        members = members_query.scalars().unique().all()
        
        team_member_tasks = []
        
        for member in members:
            user = member.user
            
            tasks_query = await db.execute(
                select(Task)
                .where(
                    and_(
                        Task.user_id == user.user_id,
                        or_(
                            and_(
                                Task.due_date >= datetime.combine(today, datetime.min.time()),
                                Task.due_date < datetime.combine(tomorrow, datetime.min.time())
                            ),
                            and_(
                                Task.due_date < datetime.combine(today, datetime.min.time()),
                                Task.status.not_in([TaskStatus.completed, TaskStatus.cancelled])
                            )
                        )
                    )
                )
                .order_by(Task.due_date.asc())
            )
            tasks = tasks_query.scalars().all()
            
            team_member_tasks.append({
                "member_id": user.user_id,
                "member_name": f"{user.first_name} {user.last_name}",
                "member_avatar": user.avatar,
                "tasks": [
                    {
                        "id": task.task_id,
                        "title": task.title,
                        "description": task.description,
                        "due_time": task.due_date.strftime("%I:%M %p"),
                        "due_date": task.due_date.isoformat(),
                        "status": task.status.value,
                        "category": task.category
                    }
                    for task in tasks
                ],
                "tasks_count": len(tasks)
            })
        
        department_tasks.append({
            "team_id": team.team_id,
            "team_name": team.name,
            "members": team_member_tasks,
            "total_tasks": sum(m["tasks_count"] for m in team_member_tasks)
        })
    
    return {
        "department_name": department.name,
        "teams": department_tasks
    }


@router.get("/ceo/stats")
async def get_ceo_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    depts_query = await db.execute(
        select(func.count(Department.department_id))
    )
    total_departments = depts_query.scalar() or 0
    
    teams_query = await db.execute(
        select(func.count(Team.team_id))
    )
    total_teams = teams_query.scalar() or 0
    
    employees_query = await db.execute(
        select(func.count(User.user_id))
        .where(User.is_active == True)
    )
    total_employees = employees_query.scalar() or 0
    
    all_tasks_query = await db.execute(
        select(Task)
    )
    all_tasks = all_tasks_query.scalars().all()
    
    total_tasks = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.completed])
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    depts_all_query = await db.execute(
        select(Department)
    )
    departments = depts_all_query.scalars().all()
    
    dept_scores = []
    for dept in departments:
        team_ids_query = await db.execute(
            select(Team.team_id)
            .where(Team.department_id == dept.department_id)
        )
        team_ids = [row[0] for row in team_ids_query.all()]
        
        if team_ids:
            member_ids_query = await db.execute(
                select(TeamMember.user_id)
                .where(TeamMember.team_id.in_(team_ids))
            )
            member_ids = [row[0] for row in member_ids_query.all()]
            
            if member_ids:
                dept_tasks_query = await db.execute(
                    select(Task)
                    .options(selectinload(Task.report))
                    .where(Task.user_id.in_(member_ids))
                )
                dept_tasks = dept_tasks_query.scalars().all()
                
                if dept_tasks:
                    dept_score = calculate_performance_score(dept_tasks)
                    dept_scores.append(dept_score)
    
    avg_dept_score = sum(dept_scores) / len(dept_scores) if dept_scores else 0.0
    
    active_projects = len([t for t in all_tasks if t.status not in [TaskStatus.completed, TaskStatus.cancelled]])
    
    culture_points_query = await db.execute(
        select(func.sum(User.culture_points))
        .where(User.is_active == True)
    )
    total_culture_points = culture_points_query.scalar() or 0
    
    return {
        "total_departments": total_departments,
        "total_teams": total_teams,
        "total_employees": total_employees,
        "task_completion_rate": f"{completion_rate:.1f}%",
        "avg_department_score": f"{avg_dept_score:.1f}/10",
        "active_projects": active_projects,
        "total_culture_points": total_culture_points
    }


@router.get("/ceo/department-overview")
async def get_ceo_department_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    depts_query = await db.execute(
        select(Department)
        .options(
            joinedload(Department.teams),
            joinedload(Department.head),
            selectinload(Department.members)
        )
    )
    departments = depts_query.scalars().unique().all()
    
    dept_overview = []
    
    for dept in departments:
        teams_count = len(dept.teams)
        active_members_count = len([m for m in dept.members if m.is_active])
        
        team_ids_query = await db.execute(
            select(Team.team_id)
            .where(Team.department_id == dept.department_id)
        )
        team_ids = [row[0] for row in team_ids_query.all()]
        
        tasks_completed = 0
        tasks_assigned = 0
        performance_score = 0.0
        
        if team_ids:
            member_ids_query = await db.execute(
                select(TeamMember.user_id)
                .where(TeamMember.team_id.in_(team_ids))
            )
            member_ids = [row[0] for row in member_ids_query.all()]
            
            if member_ids:
                dept_tasks_query = await db.execute(
                    select(Task)
                    .options(selectinload(Task.report))
                    .where(Task.user_id.in_(member_ids))
                )
                dept_tasks = dept_tasks_query.scalars().all()
                
                tasks_assigned = len(dept_tasks)
                tasks_completed = len([t for t in dept_tasks if t.status == TaskStatus.completed])
                
                performance_score = calculate_performance_score(dept_tasks)
        
        completion_rate = (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0
        
        dept_overview.append({
            "department_id": dept.department_id,
            "department_name": dept.name,
            "department_head": f"{dept.head.first_name} {dept.head.last_name}" if dept.head else "Not Assigned",
            "teams_count": teams_count,
            "active_members": active_members_count,
            "tasks_completed": tasks_completed,
            "tasks_assigned": tasks_assigned,
            "completion_rate": f"{completion_rate:.1f}%",
            "performance_score": f"{performance_score:.1f}/10"
        })
    
    return {
        "departments": dept_overview
    }


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    tasks_query = await db.execute(
        select(Task).where(Task.user_id == current_user.user_id)
    )
    all_tasks = tasks_query.scalars().all()
    
    total_tasks = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.completed])
    
    pending_reviews = len([t for t in all_tasks if t.status == TaskStatus.in_review])
    
    team_membership_query = await db.execute(
        select(TeamMember)
        .where(TeamMember.user_id == current_user.user_id)
    )
    team_membership = team_membership_query.scalar_one_or_none()
    
    team_score = 0.0
    if team_membership:
        team_member_ids_query = await db.execute(
            select(TeamMember.user_id)
            .where(TeamMember.team_id == team_membership.team_id)
        )
        team_member_ids = [row[0] for row in team_member_ids_query.all()]
        
        if team_member_ids:
            team_tasks_query = await db.execute(
                select(Task)
                .options(selectinload(Task.report))
                .where(Task.user_id.in_(team_member_ids))
            )
            team_tasks = team_tasks_query.scalars().all()
            
            team_score = calculate_performance_score(team_tasks)
    
    active_projects = len([
        t for t in all_tasks 
        if t.status not in [TaskStatus.completed, TaskStatus.cancelled]
    ])
    
    return {
        "tasks_total": total_tasks,
        "tasks_completed": completed_tasks,
        "pending_reviews": pending_reviews,
        "team_score": f"{team_score:.1f}/10",
        "active_projects": active_projects
    }


@router.get("/tasks/today")
async def get_tasks_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    tasks_query = await db.execute(
        select(Task)
        .where(
            and_(
                Task.user_id == current_user.user_id,
                or_(
                    and_(
                        Task.due_date >= datetime.combine(today, datetime.min.time()),
                        Task.due_date < datetime.combine(tomorrow, datetime.min.time())
                    ),
                    and_(
                        Task.due_date < datetime.combine(today, datetime.min.time()),
                        Task.status.not_in([TaskStatus.completed, TaskStatus.cancelled])
                    )
                )
            )
        )
        .order_by(Task.due_date.asc())
    )
    tasks = tasks_query.scalars().all()
    
    return [
        {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "due_time": task.due_date.strftime("%I:%M %p"),
            "due_date": task.due_date.isoformat(),
            "status": task.status.value,
            "category": task.category
        }
        for task in tasks
    ]


@router.get("/quick-actions")
async def get_quick_actions(current_user: User = Depends(get_current_user)):
    """
    Return a set of actions based on the user's role
    """
    role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    
    actions = []
    
    if role == "team_lead":
        actions = [
            {"label": "View Team Tasks", "url": "/dashboard/team-tasks-today"},
            {"label": "Assign Task", "url": "/dashboard/tasks/assign"},
            {"label": "View Team Performance", "url": "/dashboard/team-lead/stats"}
        ]
    elif role == "department_head":
        actions = [
            {"label": "View Department Tasks", "url": "/dashboard/department-tasks-today"},
            {"label": "View Department Performance", "url": "/dashboard/department-head/stats"}
        ]
    elif role in ["ceo", "coo"]:
        actions = [
            {"label": "View Company Stats", "url": "/dashboard/ceo/stats"},
            {"label": "View Department Overview", "url": "/dashboard/ceo/department-overview"}
        ]
    else:
        actions = [
            {"label": "View My Tasks", "url": "/dashboard/tasks/today"},
            {"label": "View My Performance", "url": "/dashboard/stats"}
        ]
    
    return actions
