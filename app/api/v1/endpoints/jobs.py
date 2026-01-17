"""API endpoints for AXI Event Application Forms with Email Notifications."""

import json
import uuid
import traceback
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from app.constants.constants import ApplicationStatus, JobStatus
from app.core.database import aget_db
from app.core.security import get_current_user
from app.models.job import Job, JobApplication
from app.models.user import User
from app.schemas.jobsSchemas import JobApplicationRequest, JobApplicationResponse, JobCreateRequest, JobResponse
from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic

from app.core.config import settings

router = APIRouter(
    prefix="/ideation-jobs",
    tags=["ideation-jobs"]
)

DUPLICATE_SUBMISSION_WINDOW = 24


def normalize_email(email: str) -> str:
    """Normalize email by converting to lowercase and stripping whitespace."""
    return email.strip().lower()


def get_graph_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="axi@ideationaxis.com"
    )

def get_graph_root_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="info@ideationaxis.com"
    )


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Create a new job posting (admin only).
    Job is automatically opened and posted_at is set.
    TODO: Add proper admin authorization check.
    """
    try:
        # Convert tags list to JSON string
        tags_json = json.dumps(request.tags)
        
        # Create job with OPEN status and set posted_at to current time
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
            status=JobStatus.OPEN,  # Auto-open the job
            posted_at=datetime.utcnow(),  # Set posting time
            closes_at=request.closes_at  # Use the closing date from request
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Parse tags for response
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
    
    except Exception as e:
        await db.rollback()
        print(f"Error creating job: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to create job posting")

@router.get("/jobs/open", response_model=List[JobResponse])
async def get_open_jobs(
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all open job positions (public endpoint).
    """
    try:
        query = select(Job).where(
            Job.status == JobStatus.OPEN
            
        ).order_by(Job.posted_at.desc())
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        # Parse tags for each job
        jobs_list = []
        for job in jobs:
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
            jobs_list.append(job_dict)
        
        return jobs_list
    
    except Exception as e:
        print(f"Error fetching open jobs: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch open jobs")
    
@router.get("/admin/jobs")  # Remove response_model=List[JobResponse]
async def get_all_jobs_admin(
    status: Optional[str] = Query(None, description="Filter by status (draft, open, closed, filled)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all job positions with optional status filter (Admin only).
    Returns jobs across all statuses: draft, open, closed, filled.
    """
    try:
        # Check admin authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim", "Kwame Yeboah Amponsah"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view all jobs"
            )
        
        # Build query
        query = select(Job)
        
        # Apply status filter if provided
        if status:
            try:
                status_enum = JobStatus(status.lower())
                query = query.where(Job.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid options: draft, open, closed, filled"
                )
        
        # Order by most recent first
        query = query.order_by(Job.posted_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        # Get total count
        count_query = select(func.count()).select_from(Job)
        if status:
            count_query = count_query.where(Job.status == status_enum)
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()
        
        # Parse tags and convert datetime to ISO string for each job
        jobs_list = []
        for job in jobs:
            job_dict = {
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
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                # Additional admin fields
                "created_by": job.created_by if hasattr(job, 'created_by') else None,
                "updated_by": job.updated_by if hasattr(job, 'updated_by') else None,
            }
            jobs_list.append(job_dict)
        
        return {
            "jobs": jobs_list,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "returned": len(jobs_list)
            },
            "summary": {
                "total_jobs": total_count,
                "filtered_by": status if status else "all statuses"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching jobs (admin): {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_by_id(
    job_id: str,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get a specific job by ID (public endpoint).
    """
    try:
        query = select(Job).where(Job.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only show open jobs to public
        if job.status != JobStatus.OPEN:
            raise HTTPException(status_code=404, detail="Job not found")
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching job: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch job")


@router.patch("/jobs/{job_id}/open")
async def open_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Open a job position (admin only).
    TODO: Add proper admin authorization check.
    """
    try:
        query = select(Job).where(Job.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.open_position()
        await db.commit()
        
        return {
            "message": "Job opened successfully",
            "job_id": job_id,
            "status": job.status.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to open job")
    
@router.get("/admin/jobs/{job_id}")
async def get_job_by_id_admin(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get a specific job by ID with full details (Admin only).
    Returns job regardless of status (draft, open, closed, filled).
    """
    try:
        # Check admin authorization
        full_name = f"{current_user.first_name} {current_user.last_name}".strip()
        authorized_users = ["Philip Appiah", "Kelvin Kanyiti Gbolo", "Bernard Ephraim", "Kwame Yeboah Amponsah"]
        
        if full_name not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view job details"
            )
        
        query = select(Job).where(Job.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        
        job_dict = {
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
            "filled_at": job.filled_at.isoformat() if hasattr(job, 'filled_at') and job.filled_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            # Additional admin metadata
            "created_by": job.created_by if hasattr(job, 'created_by') else None,
            "updated_by": job.updated_by if hasattr(job, 'updated_by') else None,
        }
        
        return job_dict
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching job (admin): {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch job")


@router.patch("/jobs/{job_id}/close")
async def close_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Close a job position (admin only).
    TODO: Add proper admin authorization check.
    """
    try:
        query = select(Job).where(Job.job_id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.close_position()
        await db.commit()
        
        return {
            "message": "Job closed successfully",
            "job_id": job_id,
            "status": job.status.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to close job")


# ============================================================================
# JOB APPLICATION ENDPOINTS
# ============================================================================

@router.post("/jobs/{job_id}/apply", response_model=JobApplicationResponse)
async def submit_job_application(
    job_id: str,
    request: JobApplicationRequest,
    db: AsyncSession = Depends(aget_db)
):
    """
    Submit an application for a job position.
    """
    try:
        # Check if job exists and is open
        job_query = select(Job).where(Job.job_id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.OPEN:
            raise HTTPException(
                status_code=400,
                detail="This position is no longer accepting applications"
            )
        
        # Normalize email
        normalized_email = normalize_email(request.email)
        
        # Check for duplicate application
        cutoff_time = datetime.utcnow() - timedelta(hours=DUPLICATE_SUBMISSION_WINDOW)
        
        duplicate_query = select(JobApplication).where(
            and_(
                JobApplication.email == normalized_email,
                JobApplication.job_id == job_id,
                JobApplication.submitted_at >= cutoff_time
            )
        )
        
        duplicate_result = await db.execute(duplicate_query)
        existing_application = duplicate_result.scalar_one_or_none()
        
        if existing_application:
            raise HTTPException(
                status_code=409,
                detail=f"You've already applied for this position within the last {DUPLICATE_SUBMISSION_WINDOW} hours."
            )
        
        # Validate why_fit length
        if len(request.why_fit) < 50:
            raise HTTPException(
                status_code=400,
                detail="Please provide more detail about why you're a good fit (minimum 50 characters)"
            )
        
        # portfolio_urls is already validated and normalized by Pydantic
        portfolio_urls = request.portfolio_urls  # This is now a list of strings
        
        # Create application
        application = JobApplication(
            application_id=str(uuid.uuid4()),
            job_id=job_id,
            full_name=request.full_name.strip(),
            email=normalized_email,
            phone_number=request.phone_number.strip() if request.phone_number else None,
            linkedin_url=str(request.linkedin_url) if request.linkedin_url else None,
            portfolio_urls=portfolio_urls,  # Store as array of strings
            why_fit=request.why_fit.strip(),
            cover_letter=request.cover_letter.strip() if request.cover_letter else None,
            status=ApplicationStatus.PENDING,
            submitted_at=datetime.utcnow()
        )
        
        db.add(application)
        
        try:
            await db.commit()
            await db.refresh(application)
        except Exception as e:
            await db.rollback()
            print(f"Database commit error: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail="Failed to submit your application. Please try again later."
            )
        
        # Send confirmation emails
        try:
            from app.constants.constants import ADMIN_EMAILS
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
                'portfolio_urls': portfolio_urls,  # Send as list
                'why_fit': request.why_fit,
                'cover_letter': request.cover_letter,
                'submitted_at': application.submitted_at
            }
            
            # Send confirmation to applicant
            user_email_result = await notify_job_application_received(
                application_data=application_data,
                graph_client=graph_client
            )
            
            if user_email_result['status'] == 'failed':
                print(f"⚠️ User confirmation email failed: {user_email_result.get('error')}")
            
            # Notify admin team
            admin_email_result = await notify_admin_new_job_application(
                application_data=application_data,
                graph_client=graph_client,
                admin_emails=ADMIN_EMAILS
            )
            
            if admin_email_result['status'] == 'failed':
                print(f"⚠️ Admin notification email failed: {admin_email_result.get('error')}")
                
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"⚠️ Failed to send emails: {str(email_error)}")
            traceback.print_exc()
        
        return JobApplicationResponse(
            message="Application submitted successfully! We'll review your application and get back to you soon.",
            application_id=application.application_id,
            job_title=job.title
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unexpected error in job application: {error_traceback}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/jobs/{job_id}/applications")
async def get_job_applications(
    job_id: str,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Get all applications for a specific job (admin only).
    TODO: Add proper admin authorization check.
    """
    try:
        # Verify job exists
        job_query = select(Job).where(Job.job_id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Build applications query
        query = select(JobApplication).where(
            JobApplication.job_id == job_id
        ).order_by(JobApplication.submitted_at.desc())
        
        if status:
            try:
                status_enum = ApplicationStatus(status)
                query = query.where(JobApplication.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status value")
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        applications = result.scalars().all()
        
        return {
            "job": {
                "job_id": job.job_id,
                "title": job.title,
                "status": job.status.value
            },
            "applications": [
                {
                    "application_id": app.application_id,
                    "full_name": app.full_name,
                    "email": app.email,
                    "phone_number": app.phone_number,
                    "linkedin_url": app.linkedin_url,
                    "portfolio_urls": app.portfolio_urls if app.portfolio_urls else [],  # Changed to portfolio_urls
                    "why_fit": app.why_fit,
                    "cover_letter": app.cover_letter,
                    "status": app.status.value,
                    "submitted_at": app.submitted_at.isoformat(),
                    "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None
                }
                for app in applications
            ],
            "total": len(applications),
            "skip": skip,
            "limit": limit
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching applications: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch applications")


@router.patch("/applications/{application_id}/status")
async def update_application_status(
    application_id: str,
    new_status: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(aget_db)
):
    """
    Update application status (admin only).
    TODO: Add proper admin authorization check.
    """
    try:
        # Validate status
        try:
            status_enum = ApplicationStatus(new_status)
        except ValueError:
            valid_statuses = [s.value for s in ApplicationStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {valid_statuses}"
            )
        
        # Get application
        query = select(JobApplication).where(
            JobApplication.application_id == application_id
        )
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Update status
        application.status = status_enum
        
        if status_enum in [ApplicationStatus.REVIEWING, ApplicationStatus.SHORTLISTED]:
            if not application.reviewed_at:
                application.reviewed_at = datetime.utcnow()
            application.reviewed_by = str(current_user.user_id)
        
        if notes:
            application.notes = notes
        
        await db.commit()
        
        return {
            "message": "Application status updated successfully",
            "application_id": application_id,
            "new_status": status_enum.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating application: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to update application status")