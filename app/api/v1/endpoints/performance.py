"""Performance Engine router for IAxOS system."""

from datetime import datetime, timedelta, date, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.leadershipreport import LeadershipReport
from app.models.team import Team, TeamMember
from app.models.user import User
from app.models.task import Task
from app.models.report import Report
from app.models.recognition import Recognition
from app.models.department import Department
from app.constants.constants import TaskStatus, RequestStatus, UserRole
from app.schemas.reportSchema import SubmitLeadershipReportRequest, SubmitReportRequest
from app.services.MicrosoftEmailNotifications import notify_leadership_report_submitted, notify_report_submitted

from app.core.config import settings
from app.services.MicrosoftGraphClient import MicrosoftGraphClient  
      
graph_client = MicrosoftGraphClient(
    tenant_id=settings.MICROSOFT_TENANT_ID,
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET
)


router = APIRouter(
    prefix="/performance",
    tags=["performance"]
)

@router.get("/stats")
async def get_performance_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get performance statistics for the current user."""
    
    tasks_query = await db.execute(
        select(Task)
        .options(joinedload(Task.report))
        .where(Task.user_id == current_user.user_id)
    )
    all_tasks = tasks_query.scalars().unique().all()
    
    total_tasks = len(all_tasks)
    completed_tasks = [t for t in all_tasks if t.status == TaskStatus.completed]
    tasks_completed_count = len(completed_tasks)
    
    completion_rate = (tasks_completed_count / total_tasks * 100) if total_tasks > 0 else 0.0
    
    # FIX: Make both timezone-aware before comparison
    on_time_tasks = []
    for task in completed_tasks:
        if task.report and task.report.submitted_at and task.due_date:
            # Ensure both have timezone info (assume UTC if naive)
            submitted_at = task.report.submitted_at
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
            
            due_date = task.due_date
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            if submitted_at <= due_date:
                on_time_tasks.append(task)
    
    on_time_rate = (len(on_time_tasks) / tasks_completed_count * 100) if tasks_completed_count > 0 else 0.0
    
    average_score = (completion_rate * 0.6 + on_time_rate * 0.4) / 10
    
    return {
        "average_score": f"{average_score:.1f}",
        "completion_rate": f"{completion_rate:.0f}%",
        "on_time_rate": f"{on_time_rate:.0f}%",
        "tasks_completed": tasks_completed_count,
        "total_points": current_user.points
    }

@router.get("/tasks")
async def get_user_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending, in_progress, completed, cancelled"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all tasks for the current user with their status and scores.
    """
    query = select(Task).where(Task.user_id == current_user.user_id)
    
    if status:
        # Map frontend status to TaskStatus enum
        status_mapping = {
            "pending": TaskStatus.pending,
            "in_progress": TaskStatus.in_progress,
            "completed": TaskStatus.completed,
            "cancelled": TaskStatus.cancelled,
            "submitted": TaskStatus.in_review,
            "approved": TaskStatus.completed
        }
        
        if status in status_mapping:
            query = query.where(Task.status == status_mapping[status])
    
    query = query.order_by(Task.due_date.desc())
    
    # Use joinedload to get the report relationship
    query = query.options(joinedload(Task.report))
    
    result = await db.execute(query)
    tasks = result.unique().scalars().all()
    
    tasks_data = []
    for task in tasks:
        status_str = task.status.value
        
        # Get report link directly from the task's report relationship
        report_link = task.report.document_link if task.report else None
        
        task_data = {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "deadline": task.due_date.strftime("%B %d, %Y at %I:%M %p") if task.due_date else None,
            "status": status_str,
            "score": None,
            "reportLink": report_link,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None
        }
        
        tasks_data.append(task_data)

    return {"tasks": tasks_data}

@router.post("/submit-report")
async def submit_report(
    report_data: SubmitReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Submit a report for a single task.
    Task will remain in in_progress status.
    """
    import uuid
    
    task_query = await db.execute(
        select(Task)
        .options(joinedload(Task.report))
        .where(
            Task.task_id == report_data.task_id,
            Task.user_id == current_user.user_id
        )
    )
    task = task_query.unique().scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found or does not belong to you"
        )
    
    if task.report:
        raise HTTPException(
            status_code=400,
            detail="This task already has a report submitted. Please contact your captain if you need to update it."
        )
    
    if task.status in [TaskStatus.completed, TaskStatus.cancelled, TaskStatus.pending]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit report for a task with status: {task.status.value}"
        )
    
    new_report = Report(
        report_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        task_id=report_data.task_id,
        document_link=report_data.document_link,
        notes=report_data.notes,
        status=RequestStatus.pending,
        submitted_at=datetime.utcnow()
    )
    
    db.add(new_report)
    
    if task.status == TaskStatus.pending:
        task.status = TaskStatus.in_progress
        if not task.started_at:
            task.started_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(new_report)
    
    # === Find the reviewer (team lead/manager) ===
    reviewer = None
    
    # Check if user is part of a team
    team_member_query = await db.execute(
        select(TeamMember)
        .options(joinedload(TeamMember.team))
        .where(TeamMember.user_id == current_user.user_id)
    )
    team_member = team_member_query.scalar_one_or_none()
    
    if team_member and team_member.team:
        # Get the team lead
        team_lead_query = await db.execute(
            select(User).where(User.user_id == team_member.team.team_lead_id)
        )
        reviewer = team_lead_query.scalar_one_or_none()
    
    # If no team lead found, try to find department head
    if not reviewer and current_user.department_id:
        dept_head_query = await db.execute(
            select(User).where(
                and_(
                    User.department_id == current_user.department_id,
                    User.role == UserRole.department_head
                )
            )
        )
        reviewer = dept_head_query.scalar_one_or_none()
    
    # === Send email notification ===
    email_result = None
    if reviewer:
        try: 
            email_result = await notify_report_submitted(
                submitter=current_user,
                reviewer=reviewer,
                task_title=task.title,
                task_description=task.description,
                report_link=report_data.document_link,
                report_notes=report_data.notes or "",
                app_url=settings.FRONTEND_URL,
                graph_client=graph_client
            )
            
        except Exception as e:
            print(f"⚠️ Error sending report submission notification: {str(e)}")
            email_result = {"status": "error", "message": str(e)}
    else:
        print(f"⚠️ No reviewer found for user {current_user.user_id}")
        email_result = {"status": "skipped", "message": "No reviewer found"}
    
    return {
        "message": "Report submitted successfully",
        "report_id": new_report.report_id,
        "task_id": task.task_id,
        "status": "pending_review",
        "reviewer_notified": reviewer.email if reviewer else None,
        "email_notification": email_result
    }

@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("month", description="Period: week, month, year"),
    limit: int = Query(10, description="Number of entries to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get performance leaderboard based on task completion.
    Uses report submission time (submitted_at) for on-time calculation.
    """
    today = datetime.utcnow()
    if period == "week":
        period_start = today - timedelta(days=7)
    elif period == "year":
        period_start = today - timedelta(days=365)
    else:  
        period_start = today - timedelta(days=30)
    
    users_query = await db.execute(
        select(User)
        .where(User.is_active == True)
        .options(joinedload(User.department))
    )
    users = users_query.scalars().unique().all()
    
    user_scores = []
    for user in users:
        tasks_query = await db.execute(
            select(Task)
            .options(joinedload(Task.report))
            .where(
                Task.user_id == user.user_id,
                Task.created_at >= period_start
            )
        )
        tasks = tasks_query.scalars().unique().all()
        
        if not tasks:
            continue
        
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.completed]
        completed_count = len(completed_tasks)
        
        completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0.0
        
        on_time_tasks = []
        for task in completed_tasks:
            if task.report and task.report.submitted_at and task.due_date:
                if task.report.submitted_at <= task.due_date:
                    on_time_tasks.append(task)
        
        on_time_rate = (len(on_time_tasks) / completed_count * 100) if completed_count > 0 else 0.0
        
        average_score = (completion_rate * 0.6 + on_time_rate * 0.4) / 10
        
        user_scores.append({
            "user": user,
            "score": average_score,
            "tasks_completed": completed_count,
            "total_tasks": total_tasks
        })
    
    user_scores.sort(key=lambda x: x['score'], reverse=True)
    user_scores = user_scores[:limit]
    
    leaderboard = []
    for rank, entry in enumerate(user_scores, start=1):
        user = entry["user"]
        leaderboard.append({
            "rank": rank,
            "name": f"{user.first_name} {user.last_name}",
            "department": user.department.name if user.department else "Unassigned",
            "score": round(entry["score"], 1),
            "trend": "stable"
        })
    
    return {"entries": leaderboard, "period": period}


@router.get("/analytics/trends")
async def get_performance_trends(
    weeks: int = Query(4, description="Number of weeks to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get performance trends over the last N weeks.
    Uses report submission time (submitted_at) for on-time calculation.
    Shows current week as Week 1.
    """
    today = datetime.utcnow()
    trends = []
    
    for i in range(weeks, 0, -1):
        week_end = today - timedelta(days=(i-1)*7)
        week_start = week_end - timedelta(days=7)
        
        tasks_query = await db.execute(
            select(Task)
            .options(joinedload(Task.report))
            .where(
                Task.user_id == current_user.user_id,
                Task.created_at >= week_start,
                Task.created_at < week_end
            )
        )
        tasks = tasks_query.scalars().unique().all()
        
        if not tasks:
            trends.append({
                "week": f"Week {i}",
                "score": 0.0
            })
            continue
        
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.completed]
        completed_count = len(completed_tasks)
        
        completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0.0
        
        on_time_tasks = []
        for task in completed_tasks:
            if task.report and task.report.submitted_at and task.due_date:
                if task.report.submitted_at <= task.due_date:
                    on_time_tasks.append(task)
        
        on_time_rate = (len(on_time_tasks) / completed_count * 100) if completed_count > 0 else 0.0
        
        average_score = (completion_rate * 0.6 + on_time_rate * 0.4) / 10
        
        trends.append({
            "week": f"Week {i}",
            "score": round(average_score, 1)
        })
    
    return {"performance_weeks": trends}


@router.get("/analytics/task-categories")
async def get_task_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get breakdown of tasks by category.
    """
    # Get all user's tasks
    tasks_query = await db.execute(
        select(Task.category, func.count(Task.task_id).label('count'))
        .where(Task.user_id == current_user.user_id)
        .group_by(Task.category)
    )
    results = tasks_query.all()
    
    total_tasks = sum([r.count for r in results])
    
    categories = []
    for result in results:
        if result.category and total_tasks > 0:
            percentage = (result.count / total_tasks) * 100
            categories.append({
                "name": result.category,
                "percentage": round(percentage, 1)
            })
    
    # Sort by percentage descending
    categories.sort(key=lambda x: x['percentage'], reverse=True)
    
    return {"task_categories": categories}


@router.get("/analytics/department-comparison")
async def get_department_comparison(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get average performance scores across all departments.
    """
    today = date.today()
    period_start = today - timedelta(days=30)
    
    dept_query = await db.execute(
        select(Department)
        .options(joinedload(Department.performance_metrics))
    )
    departments = dept_query.scalars().unique().all()
    
    dept_scores = []
    for dept in departments:
        if dept.performance_metrics:
            latest_perf = max(dept.performance_metrics, key=lambda x: x.period_end)
            
            if latest_perf.tasks_assigned > 0:
                score = (latest_perf.average_completion_rate / 10.0)
            else:
                score = 0.0
            
            dept_scores.append({
                "department": dept.name,
                "score": round(score, 1)
            })
    
    dept_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return {"department_scores": dept_scores}


@router.get("/pending-tasks")
async def get_pending_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all pending and in-progress tasks for the submit report form.
    """
    today = datetime.utcnow().date()
    
    tasks_query = await db.execute(
        select(Task)
        .where(
            Task.user_id == current_user.user_id,
            Task.status.in_([TaskStatus.in_progress])
        )
        .order_by(Task.due_date.asc())
    )
    tasks = tasks_query.scalars().all()
    
    pending_tasks = []
    for task in tasks:
        pending_tasks.append({
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "deadline": task.due_date.strftime("%B %d, %Y at %I:%M %p") if task.due_date else None,
            "status": task.status.value
        })
    
    return {"pending_tasks": pending_tasks}


@router.get("/reports")
async def get_user_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Number of reports to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all reports submitted by the current user.
    """
    query = select(Report).where(Report.user_id == current_user.user_id)
    
    if status:
        if status == "pending":
            query = query.where(Report.status == RequestStatus.pending)
        elif status == "approved":
            query = query.where(Report.status == RequestStatus.approved)
        elif status == "rejected":
            query = query.where(Report.status == RequestStatus.rejected)
    
    query = query.order_by(Report.submitted_at.desc()).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    reports_data = []
    for report in reports:
        reports_data.append({
            "id": report.report_id,
            "document_link": report.document_link,
            "notes": report.notes,
            "tasks_covered": report.tasks_covered,
            "status": report.status.value,
            "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None
        })
    
    return {"reports": reports_data}

@router.post("/submit-leadership-report")
async def submit_leadership_report(
    report_data: SubmitLeadershipReportRequest,
    review_level: Optional[str] = None,  # "team" or "leadership"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Submit a leadership report (for team leads, department heads, and senior management only).
    Regular team members CANNOT submit leadership reports.
    
    Automatically routes to the appropriate reviewer:
    - Team leads → Department head
    - Department heads → CEO
    - Department heads who are also team leads:
      * review_level="team" → themselves (as department head)
      * review_level="leadership" → CEO
    - Project managers, CEO, COO, CTO → CEO
    
    Args:
        report_data: Report submission data (includes optional task_id)
        review_level: Only applicable for users who are both department_head AND team_lead
    """
    import uuid
    
    if current_user.role not in [
        UserRole.team_lead, 
        UserRole.department_head, 
        UserRole.project_manager, 
        UserRole.ceo, 
        UserRole.coo, 
        UserRole.cto
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team leads, department heads, and senior management can submit leadership reports"
        )
    
    task = None
    if report_data.task_id:
        task_query = await db.execute(
            select(Task).where(
                Task.task_id == report_data.task_id,
                Task.user_id == current_user.user_id
            )
        )
        task = task_query.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or does not belong to you"
            )
        
        if task.status in [TaskStatus.completed, TaskStatus.cancelled]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit report for a task with status: {task.status.value}"
            )
        
        existing_report_query = await db.execute(
            select(LeadershipReport).where(LeadershipReport.task_id == report_data.task_id)
        )
        existing_report = existing_report_query.scalar_one_or_none()
        
        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This task already has a leadership report associated with it"
            )
    
    submitted_to = None
    reviewer_role = None
    
    is_dual_role = False
    if current_user.role == UserRole.department_head:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        is_dual_role = team is not None
    
    if current_user.role == UserRole.department_head and is_dual_role and review_level:
        if review_level == "team":
            submitted_to = current_user.user_id
            reviewer_role = "department_head"
        elif review_level == "leadership":
            ceo_query = await db.execute(
                select(User).where(User.role == UserRole.ceo).limit(1)
            )
            ceo = ceo_query.scalar_one_or_none()
            
            if not ceo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No CEO found in the system to review your report"
                )
            
            submitted_to = ceo.user_id
            reviewer_role = "ceo"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid review_level. Must be 'team' or 'leadership'"
            )
    
    elif current_user.role == UserRole.team_lead:
        # Team leads submit to their department head
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not assigned as a team lead of any team"
            )
        
        dept_query = await db.execute(
            select(Department).where(Department.department_id == team.department_id)
        )
        department = dept_query.scalar_one_or_none()
        
        if not department or not department.head_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your department does not have a department head assigned"
            )
        
        submitted_to = department.head_id
        reviewer_role = "department_head"
    
    elif current_user.role == UserRole.department_head:
        ceo_query = await db.execute(
            select(User).where(User.role == UserRole.ceo).limit(1)
        )
        ceo = ceo_query.scalar_one_or_none()
        
        if not ceo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CEO found in the system to review your report"
            )
        
        submitted_to = ceo.user_id
        reviewer_role = "ceo"
    
    else:
        ceo_query = await db.execute(
            select(User).where(User.role == UserRole.ceo).limit(1)
        )
        ceo = ceo_query.scalar_one_or_none()
        
        if not ceo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CEO found in the system to review your report"
            )
        
        submitted_to = ceo.user_id
        reviewer_role = "ceo"
    
    reviewer_query = await db.execute(
        select(User).where(User.user_id == submitted_to)
    )
    reviewer = reviewer_query.scalar_one_or_none()
    
    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reviewer not found in the system"
        )
    
    new_leadership_report = LeadershipReport(
        report_id=str(uuid.uuid4()),
        submitted_by=current_user.user_id,
        submitted_to=submitted_to,
        task_id=report_data.task_id,
        title=report_data.title,
        document_link=report_data.document_link,
        notes=report_data.notes,
        report_period=report_data.report_period,
        status=RequestStatus.pending,
        submitted_at=datetime.utcnow()
    )
    
    db.add(new_leadership_report)
    
    if task:
        if task.status == TaskStatus.pending:
            task.status = TaskStatus.in_progress
            if not task.started_at:
                task.started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(new_leadership_report)

    # === Send email notification to reviewer ===
    should_notify = not (
        current_user.role == UserRole.department_head and 
        is_dual_role and 
        review_level == "team" and 
        submitted_to == current_user.user_id
    )
    
    email_result = None
    if should_notify:
        try:
            task_title = task.title if task else None
            
            email_result = await notify_leadership_report_submitted(
                submitter=current_user,
                reviewer=reviewer,
                report_title=report_data.title,
                report_period=report_data.report_period,
                document_link=report_data.document_link,
                report_notes=report_data.notes,
                task_title=task_title,
                submitter_role=current_user.role.value,
                app_url=settings.FRONTEND_URL,
                graph_client=graph_client
            )
            
        except Exception as e:
            print(f"⚠️ Error sending leadership report notification: {str(e)}")
            email_result = {"status": "error", "message": str(e)}
    else:
        print(f"ℹ️ Skipping notification - Department head reviewing their own team report")
        email_result = {"status": "skipped", "message": "Self-review, no notification sent"}
    
    return {
        "message": "Leadership report submitted successfully",
        "report_id": new_leadership_report.report_id,
        "title": new_leadership_report.title,
        "task_id": new_leadership_report.task_id,
        "submitted_to": new_leadership_report.submitted_to,
        "reviewer_name": f"{reviewer.first_name} {reviewer.last_name}",
        "reviewer_role": reviewer_role,
        "status": "pending_review",
        "reviewer_notified": reviewer.email if should_notify else None,
        "email_notification": email_result
    }

@router.get("/leadership-tasks")
async def get_leadership_tasks(
    review_level: Optional[str] = None,  # "team" or "leadership"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get tasks that can be associated with a leadership report.
    
    For team leads: Tasks assigned to them by their department head
    For department heads: Tasks assigned to them by CEO
    For department heads who are also team leads:
      - review_level="team": No tasks (empty list)
      - review_level="leadership": Tasks assigned by CEO
    """
    if current_user.role not in [
        UserRole.team_lead, 
        UserRole.department_head, 
        UserRole.project_manager,
        UserRole.ceo,
        UserRole.coo,
        UserRole.cto
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team leads, department heads, and senior management can submit leadership reports"
        )
    
    # Check if user is dual role (department head AND team lead)
    is_dual_role = False
    if current_user.role == UserRole.department_head:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        is_dual_role = team is not None
    
    # Determine who assigned the tasks we should fetch
    tasks_assigned_by = None
    
    if current_user.role == UserRole.department_head and is_dual_role:
        if review_level == "team":
            # Team reports don't have associated tasks
            return {"tasks": []}
        elif review_level == "leadership":
            # Get tasks assigned by CEO
            ceo_query = await db.execute(
                select(User).where(User.role == UserRole.ceo).limit(1)
            )
            ceo = ceo_query.scalar_one_or_none()
            if ceo:
                tasks_assigned_by = ceo.user_id
        else:
            # Default to CEO tasks if no review_level specified
            ceo_query = await db.execute(
                select(User).where(User.role == UserRole.ceo).limit(1)
            )
            ceo = ceo_query.scalar_one_or_none()
            if ceo:
                tasks_assigned_by = ceo.user_id
    
    elif current_user.role == UserRole.team_lead:
        # Get department head who assigned tasks
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if team:
            dept_query = await db.execute(
                select(Department).where(Department.department_id == team.department_id)
            )
            department = dept_query.scalar_one_or_none()
            
            if department and department.head_id:
                tasks_assigned_by = department.head_id
    
    elif current_user.role == UserRole.department_head:
        # Get CEO who assigned tasks
        ceo_query = await db.execute(
            select(User).where(User.role == UserRole.ceo).limit(1)
        )
        ceo = ceo_query.scalar_one_or_none()
        if ceo:
            tasks_assigned_by = ceo.user_id
    
    else:  # project_manager, ceo, coo, cto
        # Get CEO
        ceo_query = await db.execute(
            select(User).where(User.role == UserRole.ceo).limit(1)
        )
        ceo = ceo_query.scalar_one_or_none()
        if ceo:
            tasks_assigned_by = ceo.user_id
    
    if not tasks_assigned_by:
        return {"tasks": []}
    
    # Fetch tasks assigned to current user that don't have a leadership report yet
    # and are in in_progress or completed status
    tasks_query = await db.execute(
        select(Task)
        .outerjoin(LeadershipReport, Task.task_id == LeadershipReport.task_id)
        .where(
            Task.user_id == current_user.user_id,
            Task.status.in_([TaskStatus.in_progress, TaskStatus.completed]),
            LeadershipReport.report_id.is_(None)  # No leadership report associated yet
        )
        .order_by(Task.due_date.desc())
    )
    tasks = tasks_query.scalars().all()
    
    return {
        "tasks": [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "status": task.status.value,
                "category": task.category
            }
            for task in tasks
        ]
    }
