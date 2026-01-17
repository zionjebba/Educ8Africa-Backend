# app/schemas/searchSchemas.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for intelligent search"""
    query: str = Field(..., description="Natural language search query")
    user_id: int = Field(..., description="ID of the user making the search")
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional context for the search (previous queries, filters, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Find skilled Python developers in Ghana",
                "user_id": 123,
                "context": {"previous_search": "find developers"}
            }
        }


class SearchResponse(BaseModel):
    """Response model for intelligent search"""
    intent: str = Field(..., description="Detected search intent")
    entities: Dict[str, Any] = Field(..., description="Extracted entities from the query")
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    conversational_response: str = Field(..., description="Natural language response to the user")
    filters_applied: Dict[str, Any] = Field(..., description="Filters applied to the search")
    is_restricted: bool = Field(
        default=False, 
        description="Whether this query was flagged as restricted (statistics/sensitive info)"
    )
    total: int = Field(
        default=0, 
        description="Total number of results found"
    )
    loading_message: Optional[str] = Field(
        default=None,
        description="Contextual loading message based on the query"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "find_builders",
                "entities": {
                    "role_seeking": "BUILDER",
                    "builder_type": "DEVELOPER",
                    "skills": ["Python", "Django"],
                    "location": "Ghana"
                },
                "results": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "role": "BUILDER",
                        "skills": ["Python", "Django", "React"]
                    }
                ],
                "conversational_response": "Found 5 talented Python developers in Ghana! Check out their profiles below.",
                "filters_applied": {
                    "location": "Ghana",
                    "skills": ["Python"]
                },
                "is_restricted": False,
                "total": 5
            }
        }


class SearchSuggestion(BaseModel):
    """Search suggestion model"""
    suggestions: List[str] = Field(..., description="List of suggested search queries")
    
    class Config:
        json_schema_extra = {
            "example": {
                "suggestions": [
                    "Find a technical co-founder",
                    "Connect with investors",
                    "Find beginner developers"
                ]
            }
        }