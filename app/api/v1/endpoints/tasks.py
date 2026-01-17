"""Task management router for IAxOS system."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import uuid

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.milestones import Milestone
from app.models.user import User
from app.models.task import Task
from app.models.team import Team, TeamMember
from app.constants.constants import TaskStatus, UserRole
from app.schemas.taskSchema import TaskCreateRequest, TaskStatusUpdateRequest, TaskUpdateRequest
from app.services.MicrosoftEmailNotifications import notify_multiple_tasks_assigned
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.utils.check_manager_role import check_manager_role

from app.core.config import settings
        
# Initialize Microsoft Graph client
graph_client = MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="info@ideationaxis.com"
    )

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

@router.get("/members")
async def get_team_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get team members that the current user can assign tasks to.
    Hierarchical structure:
    - CEO/COO/CTO: returns all active users in the organization
    - Department heads: returns all members in their department
    - Team leads: returns all members in their team
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can access team members"
        )
    
    members = []
    
    def format_user(user, role_in_team=None):
        return {
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "avatar": user.avatar,
            "role_in_team": role_in_team or (user.role.value if user.role else None),
            "is_current_user": user.user_id == current_user.user_id
        }
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        all_users_query = await db.execute(
            select(User)
            .where(User.is_active == True)
            .order_by(User.first_name, User.last_name)
        )
        all_users = all_users_query.scalars().all()
        
        for user in all_users:
            members.append(format_user(user))
    
    elif current_user.role == UserRole.department_head:
        if not current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not assigned to a department"
            )
        
        dept_users_query = await db.execute(
            select(User)
            .where(
                and_(
                    User.department_id == current_user.department_id,
                    User.is_active == True
                )
            )
            .order_by(User.first_name, User.last_name)
        )
        dept_users = dept_users_query.scalars().all()
        
        for user in dept_users:
            members.append(format_user(user))
    
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        team_query = await db.execute(
            select(Team)
            .where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a team lead"
            )
        
        team_members_query = await db.execute(
            select(TeamMember)
            .options(joinedload(TeamMember.user))
            .where(TeamMember.team_id == team.team_id)
        )
        team_members = team_members_query.scalars().all()
        
        for tm in team_members:
            if tm.user and tm.user.is_active:
                members.append(format_user(tm.user, tm.role_in_team))
        
        current_user_in_team = any(tm.user_id == current_user.user_id for tm in team_members)
        if not current_user_in_team:
            members.append(format_user(current_user, "Team Lead"))
    
    return {"members": members}

@router.post("/create")
async def create_task(
    task_data: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Create a new task and assign it to one or more users.
    Only managers and leads can create tasks.
    Tasks must be linked to a milestone - except for CEO who can create tasks without milestones.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can create tasks"
        )
    
    try:
        due_date = datetime.fromisoformat(task_data.due_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid due_date format. Use ISO format."
        )
    
    users_query = await db.execute(
        select(User).where(
            and_(
                User.user_id.in_(task_data.assigned_to),
                User.is_active == True
            )
        )
    )
    users = users_query.scalars().all()
    
    if len(users) != len(task_data.assigned_to):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more assigned users not found or inactive"
        )
    
    milestone_id = None
    milestone_info = None
    
    if current_user.role not in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        team_id = None
        
        if current_user.role in [UserRole.team_lead, UserRole.project_manager]:
            team_query = await db.execute(
                select(Team).where(Team.team_lead_id == current_user.user_id)
            )
            team = team_query.scalar_one_or_none()
            if team:
                team_id = team.team_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You are not assigned as a team lead"
                )
        elif current_user.role == UserRole.department_head:
            if users:
                user_team_query = await db.execute(
                    select(TeamMember)
                    .where(TeamMember.user_id == users[0].user_id)
                    .limit(1)
                )
                team_member = user_team_query.scalar_one_or_none()
                if team_member:
                    team_id = team_member.team_id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Assigned user is not part of any team"
                    )
        
        if not team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine team for milestone association. Ensure users are assigned to a team."
            )
        
        from datetime import timedelta
        current_date = datetime.utcnow()
        start_of_week = current_date - timedelta(days=current_date.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        milestone_query = await db.execute(
            select(Milestone)
            .where(
                and_(
                    Milestone.team_id == team_id,
                    Milestone.week_start_date == start_of_week
                )
            )
        )
        milestone = milestone_query.scalar_one_or_none()
        
        if not milestone:
            milestone_query = await db.execute(
                select(Milestone)
                .where(Milestone.team_id == team_id)
                .order_by(Milestone.week_start_date.desc())
                .limit(1)
            )
            milestone = milestone_query.scalar_one_or_none()
        
        if not milestone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No milestone found for this team. Please create a weekly milestone before creating tasks."
            )
        
        milestone_id = milestone.milestone_id
        milestone_info = {
            "milestone_id": milestone.milestone_id,
            "title": milestone.title,
            "week_start": milestone.week_start_date.isoformat(),
            "week_end": milestone.week_end_date.isoformat(),
            "is_current_week": milestone.week_start_date == start_of_week
        }
        
        milestone.total_tasks += len(users)
    
    created_tasks = []
    for user in users:
        task = Task(
            task_id=str(uuid.uuid4()),
            user_id=user.user_id,
            milestone_id=milestone_id,
            title=task_data.title,
            description=task_data.description,
            category=task_data.category,
            due_date=due_date,
            status=TaskStatus.pending
        )
        db.add(task)
        created_tasks.append({
            "task_id": task.task_id,
            "user_id": user.user_id,
            "user_name": f"{user.first_name} {user.last_name}",
            "milestone_id": milestone_id
        })
    
    await db.commit()

    try:
        email_results = await notify_multiple_tasks_assigned(
            assigned_users=users,
            assigner=current_user,
            task_title=task_data.title,
            task_description=task_data.description,
            task_category=task_data.category,
            due_date=due_date,
            milestone_info=milestone_info,
            app_url=settings.FRONTEND_URL,
            graph_client=graph_client
        )
        
    except Exception as e:
        print(f"⚠️ Error sending task notifications: {str(e)}")
        email_results = [{"status": "error", "message": str(e)}]
    
    response = {
        "message": "Tasks created successfully",
        "tasks_created": len(created_tasks),
        "tasks": created_tasks,
        "email_notifications": email_results
    }
    
    if milestone_info:
        response["linked_to_milestone"] = milestone_info
    
    return response


@router.get("/my-tasks")
async def get_my_tasks(
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all tasks assigned to the current user.
    Optional filters: status, category
    """
    query = select(Task).where(Task.user_id == current_user.user_id)
    
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter)
            query = query.where(Task.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    if category_filter:
        query = query.where(Task.category == category_filter)
    
    query = query.order_by(Task.due_date.asc())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "category": task.category,
                "status": task.status.value,
                "due_date": task.due_date.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "is_overdue": task.due_date < datetime.utcnow() and task.status != TaskStatus.completed,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ],
        "total": len(tasks)
    }


@router.get("/assigned-tasks")
async def get_assigned_tasks(
    status_filter: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all tasks assigned by the current user (manager/lead).
    Shows tasks they've created for their team members.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can view assigned tasks"
        )
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        query = select(Task).options(joinedload(Task.user))
    
    elif current_user.role == UserRole.department_head:
        query = select(Task).options(joinedload(Task.user)).join(
            User, Task.user_id == User.user_id
        ).where(User.department_id == current_user.department_id)
    
    else:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            return {"tasks": [], "total": 0}
        
        team_member_ids_query = await db.execute(
            select(TeamMember.user_id).where(TeamMember.team_id == team.team_id)
        )
        team_member_ids = [row[0] for row in team_member_ids_query.all()]
        
        query = select(Task).options(joinedload(Task.user)).where(
            Task.user_id.in_(team_member_ids)
        )
    
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter)
            query = query.where(Task.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    if user_id:
        query = query.where(Task.user_id == user_id)
    
    query = query.order_by(Task.due_date.asc())
    
    result = await db.execute(query)
    tasks = result.scalars().unique().all()
    
    return {
        "tasks": [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "category": task.category,
                "status": task.status.value,
                "due_date": task.due_date.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "is_overdue": task.due_date < datetime.utcnow() and task.status != TaskStatus.completed,
                "assigned_to": {
                    "user_id": task.user.user_id,
                    "name": f"{task.user.first_name} {task.user.last_name}",
                    "avatar": task.user.avatar
                },
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ],
        "total": len(tasks)
    }


@router.get("/{task_id}")
async def get_task_details(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get detailed information about a specific task.
    Users can only view their own tasks unless they're managers.
    """
    task_query = await db.execute(
        select(Task)
        .options(joinedload(Task.user))
        .where(Task.task_id == task_id)
    )
    task = task_query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.user_id != current_user.user_id and not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this task"
        )
    
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "status": task.status.value,
        "due_date": task.due_date.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "is_overdue": task.due_date < datetime.utcnow() and task.status != TaskStatus.completed,
        "assigned_to": {
            "user_id": task.user.user_id,
            "name": f"{task.user.first_name} {task.user.last_name}",
            "email": task.user.email,
            "avatar": task.user.avatar
        },
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat()
    }


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status_data: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Update the status of a task.
    Users can update their own tasks, managers can update any task.
    Updates milestone progress when task is completed.
    """
    task_query = await db.execute(
        select(Task).where(Task.task_id == task_id)
    )
    task = task_query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions
    if task.user_id != current_user.user_id and not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this task"
        )
    
    old_status = task.status
    task.status = status_data.status
    
    # Track completion for milestone
    milestone_completed_changed = False
    
    if status_data.status == TaskStatus.completed and not task.completed_at:
        task.completed_at = datetime.utcnow()
        milestone_completed_changed = True
        
        # Update milestone completed_tasks count
        if task.milestone_id:
            milestone_query = await db.execute(
                select(Milestone).where(Milestone.milestone_id == task.milestone_id)
            )
            milestone = milestone_query.scalar_one_or_none()
            if milestone:
                milestone.completed_tasks += 1
                
                # Check if all tasks are completed
                if milestone.completed_tasks >= milestone.total_tasks and not milestone.is_completed:
                    milestone.is_completed = True
                    milestone.completed_at = datetime.utcnow()
    
    # Handle un-completion (if task was completed and now set to another status)
    elif old_status == TaskStatus.completed and status_data.status != TaskStatus.completed:
        task.completed_at = None
        milestone_completed_changed = True
        
        # Update milestone completed_tasks count
        if task.milestone_id:
            milestone_query = await db.execute(
                select(Milestone).where(Milestone.milestone_id == task.milestone_id)
            )
            milestone = milestone_query.scalar_one_or_none()
            if milestone and milestone.completed_tasks > 0:
                milestone.completed_tasks -= 1
                
                # If milestone was marked complete, unmark it
                if milestone.is_completed:
                    milestone.is_completed = False
                    milestone.completed_at = None
    
    if status_data.status == TaskStatus.in_progress and not task.started_at:
        task.started_at = datetime.utcnow()
    
    if status_data.status == TaskStatus.cancelled and not task.cancelled_at:
        task.cancelled_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "message": "Task status updated successfully",
        "task_id": task.task_id,
        "old_status": old_status.value,
        "new_status": task.status.value,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "updated_at": task.updated_at.isoformat()
    }


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Update task details.
    Only managers can update tasks.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can update tasks"
        )
    
    task_query = await db.execute(
        select(Task).where(Task.task_id == task_id)
    )
    task = task_query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task_data.title:
        task.title = task_data.title
    if task_data.description:
        task.description = task_data.description
    if task_data.category:
        task.category = task_data.category
    if task_data.due_date:
        try:
            task.due_date = datetime.fromisoformat(task_data.due_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid due_date format"
            )
    if task_data.status:
        task.status = task_data.status
        if task_data.status == TaskStatus.completed and not task.completed_at:
            task.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "message": "Task updated successfully",
        "task_id": task.task_id
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Delete a task.
    Only managers can delete tasks.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can delete tasks"
        )
    
    task_query = await db.execute(
        select(Task).where(Task.task_id == task_id)
    )
    task = task_query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await db.delete(task)
    await db.commit()
    
    return {
        "message": "Task deleted successfully",
        "task_id": task_id
    }


@router.get("/stats/overview")
async def get_task_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get task statistics for the current user or their team.
    """
    if check_manager_role(current_user):
        if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
            tasks_query = await db.execute(select(Task))
        elif current_user.role == UserRole.department_head:
            tasks_query = await db.execute(
                select(Task).join(User, Task.user_id == User.user_id)
                .where(User.department_id == current_user.department_id)
            )
        else:
            team_query = await db.execute(
                select(Team).where(Team.team_lead_id == current_user.user_id)
            )
            team = team_query.scalar_one_or_none()
            
            if not team:
                return {
                    "total_tasks": 0,
                    "completed": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "overdue": 0,
                    "completion_rate": 0.0
                }
            
            team_member_ids_query = await db.execute(
                select(TeamMember.user_id).where(TeamMember.team_id == team.team_id)
            )
            team_member_ids = [row[0] for row in team_member_ids_query.all()]
            
            tasks_query = await db.execute(
                select(Task).where(Task.user_id.in_(team_member_ids))
            )
    else:
        tasks_query = await db.execute(
            select(Task).where(Task.user_id == current_user.user_id)
        )
    
    tasks = tasks_query.scalars().all()
    
    total = len(tasks)
    completed = len([t for t in tasks if t.status == TaskStatus.completed])
    pending = len([t for t in tasks if t.status == TaskStatus.pending])
    in_progress = len([t for t in tasks if t.status == TaskStatus.in_progress])
    overdue = len([
        t for t in tasks 
        if t.due_date < datetime.utcnow() and t.status != TaskStatus.completed
    ])
    
    completion_rate = (completed / total * 100) if total > 0 else 0.0
    
    return {
        "total_tasks": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "completion_rate": round(completion_rate, 1)
    }


@router.get("/categories/list")
async def get_task_categories(
    current_user: User = Depends(get_current_user),
):
    """
    Get available task categories.
    """
    categories = [
        {"id": "development", "name": "Development"},
        {"id": "design", "name": "Design"},
        {"id": "marketing", "name": "Marketing"},
        {"id": "research", "name": "Research"},
        {"id": "documentation", "name": "Documentation"},
        {"id": "meeting", "name": "Meeting"},
        {"id": "review", "name": "Review"},
        {"id": "other", "name": "Other"}
    ]
    
    return {"categories": categories}

@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status_data: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Update the status of a task.
    Users can update their own tasks, managers can update any task.
    """
    task_query = await db.execute(
        select(Task).where(Task.task_id == task_id)
    )
    task = task_query.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions
    if task.user_id != current_user.user_id and not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this task"
        )
    
    old_status = task.status
    
    task.status = status_data.status
    
    if status_data.status == TaskStatus.completed and not task.completed_at:
        task.completed_at = datetime.utcnow()
    
    if status_data.status == TaskStatus.in_progress and not task.started_at:
        task.started_at = datetime.utcnow()
    
    if status_data.status == TaskStatus.cancelled and not task.cancelled_at:
        task.cancelled_at = datetime.utcnow()
    
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "message": "Task status updated successfully",
        "task_id": task.task_id,
        "old_status": old_status.value,
        "new_status": task.status.value,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "updated_at": task.updated_at.isoformat()
    }