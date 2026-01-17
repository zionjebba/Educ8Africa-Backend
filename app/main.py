import asyncio
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from app.core.database import session_manager, aget_db
from sqlalchemy.ext.asyncio import AsyncSession

# Core routers for Educ8 Africa
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.onboarding import router as onboarding_router
from app.api.v1.endpoints.uploads import router as uploads_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.peoplestructure import router as people_structure_router
from app.api.v1.endpoints.performance import router as performance_router
from app.api.v1.endpoints.culture import router as culture_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.milestones import router as milestones_router
from app.api.v1.endpoints.recognition import router as recognition_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.jobs import router as jobs_router

# Social features
try:
    from app.api.v1.endpoints.sunday import router as sundays_router, social_sunday_scheduler
    SUNDAY_AVAILABLE = True
except ImportError:
    SUNDAY_AVAILABLE = False
    
try:
    from app.api.v1.endpoints.saturday import router as saturday_router, social_saturday_scheduler
    SATURDAY_AVAILABLE = True
except ImportError:
    SATURDAY_AVAILABLE = False

# try:
#     from app.api.v1.endpoints.eventapplications import router as eventapplications_router
#     EVENT_APPS_AVAILABLE = True
# except ImportError:
#     EVENT_APPS_AVAILABLE = False


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
import logging
from contextlib import asynccontextmanager
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

scheduler_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for app lifespan events"""
    
    try:
        logger.info("🚀 Starting Educ8 Africa application...")
        
        logger.info("🔌 Initializing database connection pool...")
        await session_manager.init()
        logger.info("✅ Database connection pool ready")
        
        # Create tables automatically
        logger.info("📊 Creating database tables...")
        from app.models.base import Base
        import app.models  # This imports all models
        
        async with session_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ All tables created!")
        
        # Start schedulers if available
        if SATURDAY_AVAILABLE:
            logger.info("📅 Starting Social Saturday Scheduler...")
            task = asyncio.create_task(social_saturday_scheduler())
            scheduler_tasks.append(task)
            logger.info("✅ Social Saturday Scheduler started")
        
        if SUNDAY_AVAILABLE:
            logger.info("📅 Starting Social Sunday Scheduler...")
            task = asyncio.create_task(social_sunday_scheduler())
            scheduler_tasks.append(task)
            logger.info("✅ Social Sunday Scheduler started")
            
    except Exception as e:
        logger.critical(f"🔥 Application startup failed: {str(e)}")
        raise
    
    try:
        logger.info("🏁 Educ8 Africa application startup complete")
        yield
    finally:
        try:
            logger.info("🛑 Beginning application shutdown...")
            
            # Cancel all scheduler tasks
            for task in scheduler_tasks:
                if not task.done():
                    logger.info("⏹️ Stopping scheduler...")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info("✅ Scheduler stopped")
            
            logger.info("🔌 Closing database connections...")
            await session_manager.close()
            logger.info("✅ Database connections closed cleanly")
        except Exception as e:
            logger.error(f"⚠️ Error during shutdown: {str(e)}")
            raise
        finally:
            logger.info("👋 Application shutdown complete")
            

app = FastAPI(
    title="Educ8 Africa API",
    description="API for Educ8 Africa - Education Management Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET_KEY,
    max_age=3600,
    same_site="none" if settings.ENVIRONMENT == "production" else "lax",
    https_only=True if settings.ENVIRONMENT == "production" else False
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Origin: {request.headers.get('origin')}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# CORS Configuration
if settings.ENVIRONMENT == "production":
    allowed_origins = [
        "https://www.educ8africa.com",
        "https://educ8africa.com",
        "https://app.educ8africa.com",
    ]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.get("/", tags=["Health Check"])
async def health_check(db: AsyncSession = Depends(aget_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "Educ8 Africa API",
            "database": "connected",
            "schedulers_running": len([t for t in scheduler_tasks if not t.done()])
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Educ8 Africa API",
            "database": "disconnected",
            "error": str(e)
        }


# Include core routers
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
app.include_router(onboarding_router, prefix="/api/v1", tags=["Onboarding"])
app.include_router(uploads_router, prefix="/api/v1", tags=["Uploads"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(people_structure_router, prefix="/api/v1", tags=["People & Structure"])
app.include_router(performance_router, prefix="/api/v1", tags=["Performance"])
app.include_router(culture_router, prefix="/api/v1", tags=["Culture"])
app.include_router(tasks_router, prefix="/api/v1", tags=["Tasks"])
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(milestones_router, prefix="/api/v1", tags=["Milestones"])
app.include_router(recognition_router, prefix="/api/v1", tags=["Recognition"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])

# Include optional routers
if SUNDAY_AVAILABLE:
    app.include_router(sundays_router, prefix="/api/v1", tags=["Social Sundays"])
    
if SATURDAY_AVAILABLE:
    app.include_router(saturday_router, prefix="/api/v1", tags=["Social Saturdays"])
    
# if EVENT_APPS_AVAILABLE:
#     app.include_router(eventapplications_router, prefix="/api/v1", tags=["Event Applications"])
    

logger.info(f"✅ Loaded {len(app.routes)} routes")