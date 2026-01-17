# app/api/v1/search.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import aget_db
from app.schemas.searchSchemas import SearchRequest, SearchResponse
from app.services.NLPService import NLPService
from app.services.SearchService import SearchService
from app.models.axiuser import AxiUser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/search",
    tags=["search"]
)


def get_nlp_service() -> NLPService:
    """Dependency for NLP service"""
    return NLPService()


def get_search_service(db: Session = Depends(aget_db)) -> SearchService:
    """Dependency for search service"""
    return SearchService(db)


@router.post("/", response_model=SearchResponse)
async def intelligent_search(
    request: SearchRequest,
    db: AsyncSession = Depends(aget_db),
    nlp_service: NLPService = Depends(get_nlp_service),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Process natural language search queries with AI-powered intent classification
    
    Handles:
    - Search intents (find_builders, find_cofounders, etc.)
    - Restricted intents (request_statistics, request_sensitive_info)
    - General questions (ask_question, get_resources)
    
    Example queries:
    - "Find skilled developers who are beginner level to join my team"
    - "Looking for a technical co-founder in Ghana"
    - "Show me fintech startups that are hiring"
    - "How many founders are on the platform?" (restricted)
    - "What are typical check sizes?" (restricted)
    
    Returns:
        SearchResponse with intent, entities, results, and conversational response
    """
    
    try:
        # Validate user exists - using async query
        result = await db.execute(select(AxiUser).filter(AxiUser.id == request.user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"Search query from user {request.user_id}: {request.query}")
        
        # Step 1: Classify intent and extract entities using NLP
        analysis = await nlp_service.analyze_query(
            query=request.query,
            user_id=request.user_id,
            context=request.context
        )
        
        logger.info(f"Intent: {analysis.intent}, Confidence: {analysis.confidence}")
        logger.info(f"Entities: {analysis.entities}")
        
        # Generate loading message based on query and intent
        loading_message = nlp_service.generate_loading_message(
            query=request.query,
            intent=analysis.intent
        )
        
        # Step 2: Handle restricted intents (statistics/sensitive info)
        if analysis.intent in ["request_statistics", "request_sensitive_info"]:
            logger.info(f"🚫 Restricted query detected: {analysis.intent}")
            
            # Generate appropriate response WITHOUT performing search
            conversational_response = nlp_service._generate_restricted_response(
                query=request.query,
                analysis=analysis
            )
            
            return SearchResponse(
                intent=analysis.intent,
                entities=analysis.entities,
                results=[],
                conversational_response=conversational_response,
                filters_applied={},
                is_restricted=True,
                total=0,
                loading_message=loading_message
            )
        
        # Step 3: Handle general questions (non-search intents)
        if analysis.intent in ["ask_question", "get_resources"]:
            logger.info(f"💬 Non-search query: {analysis.intent}")
            
            # Generate response for general questions
            conversational_response = await nlp_service.generate_response(
                query=request.query,
                results=[],
                analysis=analysis
            )
            
            return SearchResponse(
                intent=analysis.intent,
                entities=analysis.entities,
                results=[],
                conversational_response=conversational_response,
                filters_applied={},
                is_restricted=False,
                total=0,
                loading_message=loading_message
            )
        
        # Step 4: Execute search for valid search intents
        logger.info(f"🔍 Executing search for intent: {analysis.intent}")
        
        results = await search_service.execute_search(
            intent=analysis.intent,
            entities=analysis.entities,
            user_id=request.user_id,
            limit=20,
            offset=0
        )
        
        logger.info(f"✅ Found {len(results)} results")
        
        # Step 5: Generate conversational response
        response_text = await nlp_service.generate_response(
            query=request.query,
            results=results,
            analysis=analysis
        )
        
        return SearchResponse(
            intent=analysis.intent,
            entities=analysis.entities,
            results=results,
            conversational_response=response_text,
            filters_applied=analysis.filters,
            is_restricted=False,
            total=len(results),
            loading_message=loading_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/suggestions")
async def get_search_suggestions(
    user_id: int,
    db: AsyncSession = Depends(aget_db)
):
    """
    Get personalized search suggestions based on user role
    """
    try:
        # Use async query pattern
        result = await db.execute(select(AxiUser).filter(AxiUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Role-based suggestions
        suggestions = {
            "FOUNDER": [
                "Find a technical co-founder",
                "Get advice on product development",
                "Learn about fundraising",
                "Find beginner developers",
                "Connect with investors"
            ],
            "BUILDER": [
                "Find startup opportunities",
                "Get advice on career growth",
                "Learn new skills",
                "Find remote opportunities",
                "Connect with other builders"
            ],
            "INVESTOR": [
                "Find investment opportunities",
                "Connect with founders",
                "Explore fintech startups",
                "Find early-stage startups",
                "Meet potential portfolio companies"
            ],
            "MENTOR": [
                "Find founders to mentor",
                "Connect with early-stage startups",
                "Explore mentorship opportunities",
                "Find teams in your expertise area"
            ],
            "CO_FOUNDER": [
                "Find startups to join",
                "Connect with other co-founders",
                "Get advice on equity splits",
                "Find complementary skills",
                "Build your team"
            ],
            "ADVISOR": [
                "Find startups to advise",
                "Connect with founders",
                "Share your expertise",
                "Build advisory relationships",
                "Explore opportunities"
            ],
            "PARTNER": [
                "Find collaboration opportunities",
                "Connect with startups",
                "Explore partnerships",
                "Offer resources",
                "Build ecosystem connections"
            ]
        }
        
        # Get the user's role in uppercase
        user_role = user.role.value.upper() if hasattr(user.role, 'value') else str(user.role).upper()
        
        return {
            "suggestions": suggestions.get(user_role, suggestions["FOUNDER"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch suggestions")


@router.get("/health")
async def search_health_check(nlp_service: NLPService = Depends(get_nlp_service)):
    """
    Check search service health and available NLP providers
    """
    return {
        "status": "healthy",
        "active_provider": nlp_service.get_active_provider(),
        "available_providers": nlp_service.get_available_providers(),
        "restricted_intents": ["request_statistics", "request_sensitive_info"],
        "supported_intents": list(NLPService.INTENTS.keys())
    }