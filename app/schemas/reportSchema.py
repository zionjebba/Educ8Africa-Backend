from typing import Optional
from pydantic import BaseModel

from app.constants.constants import RequestStatus


class SubmitReportRequest(BaseModel):
    task_id: str
    document_link: str
    notes: Optional[str] = None
    tasks_covered: Optional[str] = None

class ReportReviewRequest(BaseModel):
    """Schema for report review."""
    status: RequestStatus
    review_notes: Optional[str] = None


class SubmitLeadershipReportRequest(BaseModel):
    title: str
    document_link: str
    notes: Optional[str] = None
    report_period: Optional[str] = None
    task_id: Optional[str] = None