"""
Job and JobApplication models for the job posting system.
"""

import uuid
from sqlalchemy import ARRAY, Column, String, Text, DateTime, Boolean, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.constants.constants import ApplicationStatus, JobStatus
from app.models.base import Base, TimestampMixin



class Job(Base, TimestampMixin):
    """Model for job postings."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(Text, nullable=False)  # JSON string of tags like ["Full-time", "Remote"]
    requirements = Column(Text, nullable=True)  # Detailed requirements
    responsibilities = Column(Text, nullable=True)  # Job responsibilities
    location = Column(String, default="Remote")
    employment_type = Column(String, default="Full-time")  # Full-time, Part-time, Contract
    experience_level = Column(String, nullable=True)  # Entry, Mid, Senior
    salary_range = Column(String, nullable=True)  # Optional salary range
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, nullable=False)
    posted_at = Column(DateTime, nullable=True)  # When job was made public
    closes_at = Column(DateTime, nullable=True)  # Application deadline
    filled_at = Column(DateTime, nullable=True)  # When position was filled
    
    # Relationships
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_posted_at', 'posted_at'),
    )

    def open_position(self):
        """Mark job as open and set posted_at timestamp."""
        self.status = JobStatus.OPEN
        if not self.posted_at:
            self.posted_at = datetime.utcnow()

    def close_position(self):
        """Mark job as closed."""
        self.status = JobStatus.CLOSED
        self.closes_at = datetime.utcnow()

    def mark_filled(self):
        """Mark job as filled."""
        self.status = JobStatus.FILLED
        self.filled_at = datetime.utcnow()


class JobApplication(Base, TimestampMixin):
    """Model for job applications."""

    __tablename__ = "job_applications"

    application_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_urls = Column(ARRAY(String), nullable=True, default=list) 
    why_fit = Column(Text, nullable=False)  # Why they should be given the position
    resume_url = Column(String, nullable=True)  # Optional resume upload
    cover_letter = Column(Text, nullable=True)  # Optional cover letter
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="applications")

    __table_args__ = (
        Index(
            'idx_application_duplicate_check',
            'email',
            'job_id',
            'submitted_at'
        ),
        Index('idx_application_status', 'status'),
        Index('idx_application_job', 'job_id', 'status'),
    )

    def mark_reviewing(self):
        """Mark application as under review."""
        self.status = ApplicationStatus.REVIEWING
        if not self.reviewed_at:
            self.reviewed_at = datetime.utcnow()

    def shortlist(self):
        """Shortlist the application."""
        self.status = ApplicationStatus.SHORTLISTED

    def reject(self):
        """Reject the application."""
        self.status = ApplicationStatus.REJECTED

    def accept(self):
        """Accept the application."""
        self.status = ApplicationStatus.ACCEPTED

    def withdraw(self):
        """Withdraw the application (by applicant)."""
        self.status = ApplicationStatus.WITHDRAWN