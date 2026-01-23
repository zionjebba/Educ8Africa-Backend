"""API endpoints for Educ8Africa Job Application Forms with Email Notifications."""

import json
import uuid
import traceback
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from app.constants.constants import ApplicationStatus, JobStatus, UserRole, ADMIN_EMAILS
from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.job import Job, JobApplication
from app.models.user import User
from app.schemas.jobsSchemas import JobApplicationRequest, JobApplicationResponse, JobCreateRequest, JobResponse
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.core.config import settings

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

DUPLICATE_SUBMISSION_WINDOW = 24  # hours


def normalize_email(email: str) -> str:
    """Normalize email by converting to lowercase and stripping whitespace."""
    return email.strip().lower()


def get_graph_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph client instance for user emails."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="no-reply@educ8africa.org"
    )


def get_graph_root_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph client instance for admin notifications."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="info@educ8africa.org"
    )


# ============================================================================ #
# JOB POSTING ENDPOINTS
# ============================================================================ #

@router.post("/", response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Create a new job posting (admin only).
    Job is automatically opened and posted_at is set.
    """
    if current_user.role not in [UserRole.admin, UserRole.hr_manager]:
        raise HTTPException(status_code=403, detail="Not authorized to create jobs")

    try:
        tags_json = json.dumps(request.tags)
        job = Job(
            job_id=str(uuid.uuid4()),
            title=request.title,
            description=request.description,
            tags=tags_json,
            requirements=request.requirements,
            responsibilities=request.responsibilities,
            location=request.location,
            employment_type=request.employment_type,
            experience_level=request.experience_level,
            salary_range=request.salary_range,
            status=JobStatus.OPEN,
            posted_at=datetime.utcnow(),
            closes_at=request.closes_at
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        job_dict = {
            "job_id": job.job_id,
            "title": job.title,
            "description": job.description,
            "tags": json.loads(job.tags),
            "requirements": job.requirements,
            "responsibilities": job.responsibilities,
            "location": job.location,
            "employment_type": job.employment_type,
            "experience_level": job.experience_level,
            "salary_range": job.salary_range,
            "status": job.status.value,
            "posted_at": job.posted_at,
            "closes_at": job.closes_at,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        return job_dict

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create job posting")


@router.get("/open", response_model=List[JobResponse])
async def get_open_jobs(db: AsyncSession = Depends(aget_db)):
    """Get all open job positions (public endpoint)."""
    try:
        query = select(Job).where(Job.status == JobStatus.OPEN).order_by(Job.posted_at.desc())
        result = await db.execute(query)
        jobs = result.scalars().all()

        jobs_list = []
        for job in jobs:
            jobs_list.append({
                "job_id": job.job_id,
                "title": job.title,
                "description": job.description,
                "tags": json.loads(job.tags),
                "requirements": job.requirements,
                "responsibilities": job.responsibilities,
                "location": job.location,
                "employment_type": job.employment_type,
                "experience_level": job.experience_level,
                "salary_range": job.salary_range,
                "status": job.status.value,
                "posted_at": job.posted_at,
                "closes_at": job.closes_at,
                "created_at": job.created_at,
                "updated_at": job.updated_at
            })
        return jobs_list
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch open jobs")


@router.get("/admin")
async def get_all_jobs_admin(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """Get all job positions with optional status filter (Admin only)."""
    if current_user.role not in [UserRole.admin, UserRole.hr_manager]:
        raise HTTPException(status_code=403, detail="Not authorized to view all jobs")

    try:
        query = select(Job)
        if status:
            try:
                status_enum = JobStatus(status.lower())
                query = query.where(Job.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.order_by(Job.posted_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        jobs = result.scalars().all()

        count_query = select(func.count()).select_from(Job)
        if status:
            count_query = count_query.where(Job.status == status_enum)
        total_count = (await db.execute(count_query)).scalar_one()

        jobs_list = []
        for job in jobs:
            jobs_list.append({
                "job_id": job.job_id,
                "title": job.title,
                "description": job.description,
                "tags": json.loads(job.tags) if job.tags else [],
                "requirements": job.requirements,
                "responsibilities": job.responsibilities,
                "location": job.location,
                "employment_type": job.employment_type,
                "experience_level": job.experience_level,
                "salary_range": job.salary_range,
                "status": job.status.value,
                "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                "closes_at": job.closes_at.isoformat() if job.closes_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            })

        return {
            "jobs": jobs_list,
            "pagination": {"total": total_count, "skip": skip, "limit": limit, "returned": len(jobs_list)},
            "summary": {"total_jobs": total_count, "filtered_by": status if status else "all statuses"}
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")


# ============================================================================ #
# JOB APPLICATION ENDPOINTS
# ============================================================================ #

@router.post("/{job_id}/apply", response_model=JobApplicationResponse)
async def submit_job_application(
    job_id: str,
    request: JobApplicationRequest,
    db: AsyncSession = Depends(aget_db)
):
    """
    Submit an application for a job position.
    """
    try:
        job = (await db.execute(select(Job).where(Job.job_id == job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != JobStatus.OPEN:
            raise HTTPException(status_code=400, detail="Position is not accepting applications")

        normalized_email = normalize_email(request.email)
        cutoff_time = datetime.utcnow() - timedelta(hours=DUPLICATE_SUBMISSION_WINDOW)
        duplicate = (await db.execute(
            select(JobApplication).where(
                and_(JobApplication.email == normalized_email,
                     JobApplication.job_id == job_id,
                     JobApplication.submitted_at >= cutoff_time)
            )
        )).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Already applied in the last {DUPLICATE_SUBMISSION_WINDOW} hours.")

        if len(request.why_fit) < 50:
            raise HTTPException(status_code=400, detail="Please provide more detail about why you're a good fit (min 50 chars)")

        application = JobApplication(
            application_id=str(uuid.uuid4()),
            job_id=job_id,
            full_name=request.full_name.strip(),
            email=normalized_email,
            phone_number=request.phone_number.strip() if request.phone_number else None,
            linkedin_url=str(request.linkedin_url) if request.linkedin_url else None,
            portfolio_urls=request.portfolio_urls,
            why_fit=request.why_fit.strip(),
            cover_letter=request.cover_letter.strip() if request.cover_letter else None,
            status=ApplicationStatus.PENDING,
            submitted_at=datetime.utcnow()
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)

        # Send emails
        from app.services.EventApplicationConfirmationEmail import (
            notify_job_application_received,
            notify_admin_new_job_application
        )
        graph_client = get_graph_root_client()
        application_data = {
            'email': normalized_email,
            'full_name': request.full_name,
            'application_id': application.application_id,
            'job_title': job.title,
            'phone_number': request.phone_number,
            'linkedin_url': request.linkedin_url,
            'portfolio_urls': request.portfolio_urls,
            'why_fit': request.why_fit,
            'cover_letter': request.cover_letter,
            'submitted_at': application.submitted_at
        }
        await notify_job_application_received(application_data, graph_client)
        await notify_admin_new_job_application(application_data, graph_client, admin_emails=ADMIN_EMAILS)

        return JobApplicationResponse(
            message="Application submitted successfully! We'll review your application and get back to you soon.",
            application_id=application.application_id,
            job_title=job.title
        )

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error while submitting application")
