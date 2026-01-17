"""Report review router for IAxOS system."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select, and_, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.leadershipreport import LeadershipReport
from app.models.user import User
from app.models.report import Report
from app.models.team import Team, TeamMember
from app.constants.constants import RequestStatus, UserRole, TaskStatus
from app.schemas.reportSchema import ReportReviewRequest
from app.services.MicrosoftEmailNotifications import notify_leadership_report_reviewed, notify_report_reviewed, notify_task_under_review
from app.services.MicrosoftGraphClient import MicrosoftGraphClient
from app.utils.check_manager_role import check_manager_role

from app.core.config import settings        
graph_client = MicrosoftGraphClient(
    tenant_id=settings.MICROSOFT_TENANT_ID,
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET
)

router = APIRouter(
    prefix="/reports",
    tags=["reports"]
)

@router.get("/pending-reviews")
async def get_pending_reviews(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all reports that need review by the current user.
    For team leads: returns reports from their team members (all statuses).
    For department heads: returns reviewed reports from their department + pending reports if they're also a team lead.
    For CEO/COO/CTO: returns only reviewed reports (approved/rejected).
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can review reports"
        )
    
    reports = []
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        query = select(Report).options(
            joinedload(Report.user),
            joinedload(Report.task)
        ).where(
            Report.status.in_([RequestStatus.approved, RequestStatus.rejected])
        )
        
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter)
                query = query.where(Report.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        query = query.order_by(Report.submitted_at.desc())
        result = await db.execute(query)
        reports = result.scalars().unique().all()
    
    elif current_user.role == UserRole.department_head:
        if not current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not assigned to a department"
            )
        
        # Fetch reviewed reports from department
        reviewed_query = select(Report).options(
            joinedload(Report.user),
            joinedload(Report.task)
        ).join(User, Report.user_id == User.user_id).where(
            and_(
                User.department_id == current_user.department_id,
                Report.status.in_([RequestStatus.approved, RequestStatus.rejected])
            )
        )
        
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter)
                reviewed_query = reviewed_query.where(Report.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        reviewed_query = reviewed_query.order_by(Report.submitted_at.desc())
        reviewed_result = await db.execute(reviewed_query)
        reports = list(reviewed_result.scalars().unique().all())
        
        # Check if department head is also a team lead
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        dept_head_team = team_query.scalar_one_or_none()
        
        if dept_head_team:
            team_member_ids_query = await db.execute(
                select(TeamMember.user_id).where(TeamMember.team_id == dept_head_team.team_id)
            )
            team_member_ids = [row[0] for row in team_member_ids_query.all()]
            
            # Fetch pending reports from team members
            pending_query = select(Report).options(
                joinedload(Report.user),
                joinedload(Report.task)
            ).where(
                and_(
                    Report.user_id.in_(team_member_ids),
                    Report.status == RequestStatus.pending
                )
            )
            
            if status_filter:
                try:
                    status_enum = RequestStatus(status_filter)
                    pending_query = pending_query.where(Report.status == status_enum)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {status_filter}"
                    )
            
            pending_query = pending_query.order_by(Report.submitted_at.desc())
            pending_result = await db.execute(pending_query)
            pending_reports = list(pending_result.scalars().unique().all())
            
            # Combine both lists
            reports.extend(pending_reports)
            # Sort combined results
            reports = sorted(reports, key=lambda r: r.submitted_at, reverse=True)
    
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            return {"reports": [], "total": 0}
        
        team_member_ids_query = await db.execute(
            select(TeamMember.user_id).where(TeamMember.team_id == team.team_id)
        )
        team_member_ids = [row[0] for row in team_member_ids_query.all()]
        
        query = select(Report).options(
            joinedload(Report.user),
            joinedload(Report.task)
        ).where(Report.user_id.in_(team_member_ids))
        
        if status_filter:
            try:
                status_enum = RequestStatus(status_filter)
                query = query.where(Report.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        query = query.order_by(Report.submitted_at.desc())
        result = await db.execute(query)
        reports = result.scalars().unique().all()
    
    return {
        "reports": [
            {
                "report_id": report.report_id,
                "user_id": report.user_id,
                "task_id": report.task_id,
                "document_link": report.document_link,
                "notes": report.notes,
                "status": report.status.value,
                "submitted_at": report.submitted_at.isoformat(),
                "reviewed_by": report.reviewed_by,
                "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
                "user": {
                    "user_id": report.user.user_id,
                    "name": f"{report.user.first_name} {report.user.last_name}",
                    "email": report.user.email,
                    "avatar": report.user.avatar
                },
                "task": {
                    "task_id": report.task.task_id,
                    "status": report.task.status,
                    "title": report.task.title,
                    "category": report.task.category,
                    "due_date": report.task.due_date.isoformat()
                } if report.task else None
            }
            for report in reports
        ],
        "total": len(reports)
    }

@router.patch("/{report_id}/review")
async def review_report(
    report_id: str,
    review_data: ReportReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Review a report (approve or reject).
    Only managers can review reports.
    Updates the associated task status when approved.
    
    Points system:
    - Reviewer: Gets 15 points for reviewing (approve or reject)
    - Submitter (on approval): Gets 10 points for completion + 5 bonus if on-time
    - Submitter (on rejection): No points awarded or deducted
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can review reports"
        )
    
    report_query = await db.execute(
        select(Report)
        .options(joinedload(Report.user), joinedload(Report.task))
        .where(Report.report_id == report_id)
    )
    report = report_query.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    can_review = False
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        can_review = True
    elif current_user.role == UserRole.department_head:
        if report.user.department_id == current_user.department_id:
            can_review = True
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if team:
            team_member_query = await db.execute(
                select(TeamMember).where(
                    and_(
                        TeamMember.team_id == team.team_id,
                        TeamMember.user_id == report.user_id
                    )
                )
            )
            if team_member_query.scalar_one_or_none():
                can_review = True
    
    if not can_review:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to review this report"
        )
    
    if review_data.status not in [RequestStatus.approved, RequestStatus.rejected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be either 'approved' or 'rejected'"
        )
    
    if review_data.status == RequestStatus.rejected and not review_data.review_notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review notes are required when rejecting a report"
        )
    
    if report.status in [RequestStatus.approved, RequestStatus.rejected]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This report has already been reviewed"
        )
    
    report.status = review_data.status
    report.reviewed_by = current_user.user_id
    report.reviewed_at = datetime.utcnow()
    
    submitter_points = 0
    reviewer_points = 15
    
    current_user.points += reviewer_points
    
    if review_data.status == RequestStatus.approved and report.task:
        report.task.status = TaskStatus.completed
        if not report.task.completed_at:
            report.task.completed_at = datetime.utcnow()
        
        submitter_points = 10 
        
        if report.task.due_date and report.submitted_at <= report.task.due_date:
            submitter_points += 5  
        
        report.user.points += submitter_points
    
    await db.commit()
    await db.refresh(report)
    await db.refresh(current_user)
    try:
        await notify_report_reviewed(
            submitter=report.user,
            reviewer=current_user,
            task_title=report.task.title if report.task else "Task",
            task_description=report.task.description if report.task else "",
            review_status=review_data.status.value,
            review_notes=review_data.review_notes,
            points_awarded=submitter_points,
            app_url=settings.FRONTEND_URL or "https://ideationaxis.com",
            graph_client=graph_client
        )
    except Exception as e:
        print(f"⚠️ Failed to send review notification: {e}")
    
    points_info = {
        "reviewer_points_awarded": reviewer_points,
        "reviewer_total_points": current_user.points
    }
    
    if review_data.status == RequestStatus.approved:
        points_info["submitter_points_awarded"] = submitter_points
        points_info["submitter_total_points"] = report.user.points
    
    return {
        "message": f"Report {review_data.status.value} successfully",
        "report_id": report.report_id,
        "status": report.status.value,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at.isoformat(),
        "task_updated": report.task_id is not None and review_data.status == RequestStatus.approved,
        "points": points_info
    }

@router.get("/my-reviews")
async def get_my_reviewed_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all reports reviewed by the current user.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can access this endpoint"
        )
    
    query = select(Report).options(
        joinedload(Report.user),
        joinedload(Report.task)
    ).where(
        Report.reviewed_by == current_user.user_id
    ).order_by(Report.reviewed_at.desc())
    
    result = await db.execute(query)
    reports = result.scalars().unique().all()
    
    return {
        "reports": [
            {
                "report_id": report.report_id,
                "user": {
                    "user_id": report.user.user_id,
                    "name": f"{report.user.first_name} {report.user.last_name}",
                    "email": report.user.email,
                    "avatar": report.user.avatar
                },
                "task": {
                    "task_id": report.task.task_id,
                    "title": report.task.title,
                    "category": report.task.category
                } if report.task else None,
                "document_link": report.document_link,
                "status": report.status.value,
                "submitted_at": report.submitted_at.isoformat(),
                "reviewed_at": report.reviewed_at.isoformat()
            }
            for report in reports
        ],
        "total": len(reports)
    }


@router.get("/stats/review-summary")
async def get_review_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get review statistics for the current reviewer.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can access this endpoint"
        )
    
    query = select(Report).options(joinedload(Report.user))
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        pass
    elif current_user.role == UserRole.department_head:
        query = query.join(User, Report.user_id == User.user_id).where(
            User.department_id == current_user.department_id
        )
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if not team:
            return {
                "total_reports": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "reviewed_by_me": 0,
                "approval_rate": 0.0
            }
        
        team_member_ids_query = await db.execute(
            select(TeamMember.user_id).where(TeamMember.team_id == team.team_id)
        )
        team_member_ids = [row[0] for row in team_member_ids_query.all()]
        query = query.where(Report.user_id.in_(team_member_ids))
    
    result = await db.execute(query)
    reports = result.scalars().unique().all()
    
    total = len(reports)
    pending = len([r for r in reports if r.status == RequestStatus.pending])
    approved = len([r for r in reports if r.status == RequestStatus.approved])
    rejected = len([r for r in reports if r.status == RequestStatus.rejected])
    reviewed_by_me = len([r for r in reports if r.reviewed_by == current_user.user_id])
    
    reviewed_total = approved + rejected
    approval_rate = (approved / reviewed_total * 100) if reviewed_total > 0 else 0.0
    
    return {
        "total_reports": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "reviewed_by_me": reviewed_by_me,
        "approval_rate": round(approval_rate, 1)
    }


@router.patch("/{report_id}/set-under-review")
async def set_report_under_review(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Set a report's associated task to 'in_review' status.
    Only managers can set tasks under review.
    """
    if not check_manager_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and leads can set tasks under review"
        )
    
    report_query = await db.execute(
        select(Report)
        .options(joinedload(Report.user), joinedload(Report.task))
        .where(Report.report_id == report_id)
    )
    report = report_query.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if not report.task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is not associated with a task"
        )
    
    can_review = False
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        can_review = True
    elif current_user.role == UserRole.department_head:
        if report.user.department_id == current_user.department_id:
            can_review = True
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        
        if team:
            team_member_query = await db.execute(
                select(TeamMember).where(
                    and_(
                        TeamMember.team_id == team.team_id,
                        TeamMember.user_id == report.user_id
                    )
                )
            )
            if team_member_query.scalar_one_or_none():
                can_review = True
    
    if not can_review:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage this report"
        )
    
    if report.task.status == TaskStatus.in_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already under review"
        )
    
    if report.task.status != TaskStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot set task to review from current status: {report.task.status.value}"
        )
    
    report.task.status = TaskStatus.in_review
    
    await db.commit()
    await db.refresh(report)
    await db.refresh(report.task)
    
    # === Send email notification ===
    email_result = None
    try:
        email_result = await notify_task_under_review(
            assigned_user=report.user,
            reviewer=current_user,
            task_title=report.task.title,
            task_description=report.task.description,
            report_link=report.document_link,
            app_url=settings.FRONTEND_URL,
            graph_client=graph_client
        )
        
    except Exception as e:
        print(f"⚠️ Error sending under review notification: {str(e)}")
        email_result = {"status": "error", "message": str(e)}
    
    return {
        "message": "Task set to under review successfully",
        "report_id": report.report_id,
        "task_id": report.task.task_id,
        "task_status": report.task.status.value,
        "task_title": report.task.title,
        "email_notification": email_result
    }

@router.get("/leadership-reports/pending")
async def get_pending_leadership_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all leadership reports that need review by the current user.
    Returns reports where the current user is the designated reviewer.
    """
    # Check if user has permission to review leadership reports
    if current_user.role not in [UserRole.department_head, UserRole.ceo, UserRole.coo, UserRole.cto, UserRole.project_manager]:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to review leadership reports"
        )
    
    query = (
        select(LeadershipReport)
        .options(
            joinedload(LeadershipReport.submitter).joinedload(User.department),
            joinedload(LeadershipReport.reviewer)
        )
        .where(
            LeadershipReport.submitted_to == current_user.user_id,
            LeadershipReport.status == RequestStatus.pending
        )
        .order_by(LeadershipReport.submitted_at.desc())
    )
    
    result = await db.execute(query)
    reports = result.scalars().unique().all()
    
    return {
        "reports": [
            {
                "report_id": report.report_id,
                "title": report.title,
                "document_link": report.document_link,
                "notes": report.notes,
                "report_period": report.report_period,
                "status": report.status.value,
                "submitted_at": report.submitted_at.isoformat(),
                "submitted_by": {
                    "user_id": report.submitter.user_id,
                    "name": f"{report.submitter.first_name} {report.submitter.last_name}",
                    "email": report.submitter.email,
                    "avatar": report.submitter.avatar,
                    "role": report.submitter.role.value,
                    "department": report.submitter.department.name if report.submitter.department else None
                },
                "reviewer": {
                    "user_id": report.reviewer.user_id,
                    "name": f"{report.reviewer.first_name} {report.reviewer.last_name}",
                    "email": report.reviewer.email
                } if report.reviewer else None
            }
            for report in reports
        ],
        "total": len(reports)
    }

@router.patch("/leadership-reports/{report_id}/review")
async def review_leadership_report(
    report_id: str,
    review_data: ReportReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Review a leadership report (approve or reject).
    """
    if current_user.role not in [UserRole.department_head, UserRole.ceo, UserRole.coo, UserRole.cto, UserRole.project_manager]:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to review leadership reports"
        )
    
    report_query = await db.execute(
        select(LeadershipReport)
        .options(
            joinedload(LeadershipReport.submitter),
            joinedload(LeadershipReport.task)
        )
        .where(LeadershipReport.report_id == report_id)
    )
    report = report_query.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Leadership report not found"
        )
    
    if report.submitted_to != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not the designated reviewer for this report"
        )
    
    if report.status != RequestStatus.pending:
        raise HTTPException(
            status_code=400,
            detail="This report has already been reviewed"
        )
    
    if review_data.status not in [RequestStatus.approved, RequestStatus.rejected]:
        raise HTTPException(
            status_code=400,
            detail="Status must be either 'approved' or 'rejected'"
        )
    
    if review_data.status == RequestStatus.rejected and not review_data.review_notes:
        raise HTTPException(
            status_code=400,
            detail="Review notes are required when rejecting a report"
        )
    
    report.status = review_data.status
    report.reviewed_at = datetime.utcnow()
    report.review_notes = review_data.review_notes

    submitter_points = 0
    reviewer_points = 15
    
    current_user.points += reviewer_points
    
    if review_data.status == RequestStatus.approved and report.task:
        # Update task status to completed
        report.task.status = TaskStatus.completed
        if not report.task.completed_at:
            report.task.completed_at = datetime.utcnow()
        
        # Award points to submitter
        submitter_points = 10  # Base completion points
        
        # Bonus for on-time submission
        if report.task.due_date and report.submitted_at <= report.task.due_date:
            submitter_points += 5
        
        report.submitter.points += submitter_points
    
    await db.commit()
    await db.refresh(report)

    try:
        task_title = report.task.title if report.task else None
        task_completed = (
            report.task.status == TaskStatus.completed 
            if report.task 
            else False
        )
        
        email_result = await notify_leadership_report_reviewed(
            submitter=report.submitter,
            reviewer=current_user,
            report_title=report.title,
            report_period=report.report_period,
            review_status=review_data.status.value,
            review_notes=review_data.review_notes,
            points_awarded=submitter_points,
            task_title=task_title,
            task_completed=task_completed,
            submitter_role=report.submitter.role.value,
            app_url=settings.FRONTEND_URL,
            graph_client=graph_client
        )
    
    except Exception as e:
        print(f"⚠️ Failed to send leadership report review notification: {e}")
        email_result = {"status": "error", "message": str(e)}

    points_info = {
        "reviewer_points_awarded": reviewer_points,
        "reviewer_total_points": current_user.points
    }
    
    if review_data.status == RequestStatus.approved:
        points_info["submitter_points_awarded"] = submitter_points
        points_info["submitter_total_points"] = report.submitter.points
        points_info["task_updated"] = report.task_id is not None
    
    return {
        "message": f"Leadership report {review_data.status.value} successfully",
        "report_id": report.report_id,
        "title": report.title,
        "task_id": report.task_id,
        "status": report.status.value,
        "reviewed_at": report.reviewed_at.isoformat(),
        "submitted_by": report.submitter.user_id,
        "points": points_info,
        "submitter_notified": report.submitter.email,
        "email_notification": email_result
    }

@router.get("/check-dual-role")
async def check_dual_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Check if user is both department head and team lead"""
    is_dual_role = False
    
    if current_user.role == UserRole.department_head:
        team_query = await db.execute(
            select(Team).where(Team.team_lead_id == current_user.user_id)
        )
        team = team_query.scalar_one_or_none()
        is_dual_role = team is not None
    
    return {
        "is_dual_role": is_dual_role,
        "role": current_user.role.value
    }



@router.get("/leadership-reports/reviewed")
async def get_reviewed_leadership_reports(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all reviewed leadership reports (approved or rejected).
    For CEO/COO/CTO: Returns all reviewed leadership reports
    For Department Heads: Returns their submitted reports that have been reviewed
    For Team Leads: Returns their submitted reports that have been reviewed
    """
    query = (
        select(LeadershipReport)
        .options(
            joinedload(LeadershipReport.submitter).joinedload(User.department),
            joinedload(LeadershipReport.reviewer),
            joinedload(LeadershipReport.task)
        )
        .where(
            LeadershipReport.status.in_([RequestStatus.approved, RequestStatus.rejected])
        )
    )
    
    if current_user.role in [UserRole.ceo, UserRole.coo, UserRole.cto]:
        pass
    elif current_user.role == UserRole.department_head:
        query = query.where(
            or_(
                LeadershipReport.submitted_by == current_user.user_id,  # Reports they submitted
                LeadershipReport.submitted_to == current_user.user_id   # Reports they reviewed
            )
        )
    elif current_user.role in [UserRole.team_lead, UserRole.project_manager]:
        query = query.where(LeadershipReport.submitted_by == current_user.user_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view leadership reports"
        )
    
    if status_filter and status_filter != "all":
        try:
            status_enum = RequestStatus(status_filter)
            query = query.where(LeadershipReport.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    query = query.order_by(LeadershipReport.reviewed_at.desc())
    
    result = await db.execute(query)
    reports = result.scalars().unique().all()
    
    return {
        "reports": [
            {
                "report_id": report.report_id,
                "title": report.title,
                "document_link": report.document_link,
                "notes": report.notes,
                "report_period": report.report_period,
                "status": report.status.value,
                "submitted_at": report.submitted_at.isoformat(),
                "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
                "review_notes": report.review_notes,
                "submitted_by": {
                    "user_id": report.submitter.user_id,
                    "name": f"{report.submitter.first_name} {report.submitter.last_name}",
                    "email": report.submitter.email,
                    "avatar": report.submitter.avatar,
                    "role": report.submitter.role.value,
                    "department": report.submitter.department.name if report.submitter.department else None
                },
                "reviewer": {
                    "user_id": report.reviewer.user_id,
                    "name": f"{report.reviewer.first_name} {report.reviewer.last_name}",
                    "email": report.reviewer.email,
                    "role": report.reviewer.role.value
                } if report.reviewer else None,
                "task": {
                    "task_id": report.task.task_id,
                    "title": report.task.title,
                    "status": report.task.status.value if hasattr(report.task.status, 'value') else report.task.status
                } if report.task else None
            }
            for report in reports
        ],
        "total": len(reports),
        "approved_count": len([r for r in reports if r.status == RequestStatus.approved]),
        "rejected_count": len([r for r in reports if r.status == RequestStatus.rejected])
    }