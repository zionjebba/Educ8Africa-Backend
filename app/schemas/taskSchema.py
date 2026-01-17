from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.constants.constants import TaskStatus


class TaskResponse(BaseModel):
    task_id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    due_date: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class TaskCreateRequest(BaseModel):
    """Request schema for creating a new task."""
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category: str
    due_date: str
    assigned_to: List[str] = Field(..., min_items=1)


class TaskUpdateRequest(BaseModel):
    """Request schema for updating a task."""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskStatusUpdateRequest(BaseModel):
    """Request schema for updating task status."""
    status: TaskStatus


class TeamMemberResponse(BaseModel):
    """Response schema for team member."""
    user_id: str
    first_name: str
    last_name: str
    email: str
    avatar: Optional[str] = None
    role_in_team: Optional[str] = None

