from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from typing import List, Optional, Union
from datetime import datetime


# Job Schemas
class JobCreateRequest(BaseModel):
    """Schema for creating a new job posting."""
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    tags: List[str] = Field(..., min_items=1)
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    location: str = Field(default="Remote")
    employment_type: str = Field(default="Full-time")
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    closes_at: datetime


class JobUpdateRequest(BaseModel):
    """Schema for updating a job posting."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    tags: Optional[List[str]] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    status: Optional[str] = None


class JobResponse(BaseModel):
    """Schema for job response."""
    job_id: str
    title: str
    description: str
    tags: List[str]
    requirements: Optional[str]
    responsibilities: Optional[str]
    location: str
    employment_type: str
    experience_level: Optional[str]
    salary_range: Optional[str]
    status: str
    posted_at: Optional[datetime]
    closes_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Job Application Schemas
class PortfolioUrlSchema(BaseModel):
    """Schema for individual portfolio/website/social media URL."""
    url: HttpUrl

    @validator('url', pre=True)
    def validate_url(cls, v):
        if v and isinstance(v, str) and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v


class JobApplicationRequest(BaseModel):
    """Schema for submitting a job application."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    linkedin_url: Optional[HttpUrl] = None
    portfolio_urls: List[Union[HttpUrl, PortfolioUrlSchema]] = Field(..., min_items=1, description="At least one portfolio/website/social media link is required")
    why_fit: str = Field(..., min_length=50, description="Why you should be given this position (minimum 50 characters)")
    cover_letter: Optional[str] = None

    @validator('linkedin_url', pre=True)
    def validate_linkedin_url(cls, v):
        if v and isinstance(v, str) and v.strip() == "":
            return None
        if v and isinstance(v, str) and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v
    
    @validator('portfolio_urls', pre=True)
    def validate_portfolio_urls_format(cls, v):
        """Handle both string URLs and object URLs."""
        if not v:
            raise ValueError("At least one portfolio/website/social media link is required")
        
        # If it's already a list, return it as-is
        if isinstance(v, list):
            return v
        
        # If it's a single string, wrap it in a list
        if isinstance(v, str):
            return [v]
        
        return v
    
    @validator('portfolio_urls')
    def validate_portfolio_urls_content(cls, v):
        """Validate and normalize portfolio URLs."""
        if not v:
            raise ValueError("At least one portfolio/website/social media link is required")
        
        normalized_urls = []
        for item in v:
            if isinstance(item, PortfolioUrlSchema):
                # Extract URL from the object
                url = str(item.url)
                if url and url.strip():
                    normalized_urls.append(url)
            elif isinstance(item, str):
                # It's already a string URL
                if item and item.strip():
                    # Ensure it has http/https prefix
                    if not item.startswith(('http://', 'https://')):
                        item = f"https://{item}"
                    normalized_urls.append(item)
            elif isinstance(item, HttpUrl):
                # It's a Pydantic HttpUrl object
                url = str(item)
                if url and url.strip():
                    normalized_urls.append(url)
            else:
                # Try to convert to string
                try:
                    url = str(item)
                    if url and url.strip():
                        if not url.startswith(('http://', 'https://')):
                            url = f"https://{url}"
                        normalized_urls.append(url)
                except:
                    raise ValueError(f"Invalid portfolio URL format: {item}")
        
        # Filter out any empty URLs
        normalized_urls = [url for url in normalized_urls if url.strip()]
        
        if not normalized_urls:
            raise ValueError("At least one valid portfolio/website/social media link is required")
        
        # Return as a list of strings for easier processing
        return normalized_urls


class JobApplicationResponse(BaseModel):
    """Schema for job application response."""
    message: str
    application_id: str
    job_title: str


class JobApplicationDetailResponse(BaseModel):
    """Schema for detailed job application."""
    application_id: str
    job_id: str
    job_title: str
    full_name: str
    email: str
    phone_number: Optional[str]
    linkedin_url: Optional[str]
    portfolio_urls: Optional[List[str]]  # Changed from portfolio_url to portfolio_urls (list)
    why_fit: str
    resume_url: Optional[str]
    cover_letter: Optional[str]
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True