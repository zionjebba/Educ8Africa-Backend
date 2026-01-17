import os
import hashlib
import logging
from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from typing import ClassVar, List, Optional

# Load environment variables from .env file
load_dotenv(".env", override=True)
logger = logging.getLogger(__name__)


def hash_key(key: str) -> str:
    """Hash the key using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


class Settings(BaseSettings):
    """Class to store all the settings of the Educ8Africa application."""

    # ------------------------------
    # Database - Required
    # ------------------------------
    APOSTGRES_DATABASE_URL: str = Field(env="APOSTGRES_DATABASE_URL")
    APOSTGRES_PRODUCTION_DATABASE_URL: str = Field(env="APOSTGRES_PRODUCTION_DATABASE_URL")
    
    # ------------------------------
    # API Keys - Optional
    # ------------------------------
    HASHED_API_KEY: str = Field(default="dev-hashed-key", env="HASHED_API_KEY")
    
    # ------------------------------
    # AWS - Optional (for file uploads, S3)
    # ------------------------------
    AWS_ACCESS_KEY_ID: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: str = Field(default="", env="AWS_S3_BUCKET")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_S3_BASE_URL: str = Field(default="", env="AWS_S3_BASE_URL")
    
    # ------------------------------
    # Email - Optional
    # ------------------------------
    SENDGRID_API_KEY: str = Field(default="", env="SENDGRID_API_KEY")
    FROM_EMAIL: str = Field(default="no-reply@educ8africa.com", env="FROM_EMAIL")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "no-reply@educ8africa.com")
    
    # ------------------------------
# Microsoft Auth - Required for Educ8Africa
# ------------------------------
    MICROSOFT_CLIENT_ID: str = Field(env="MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: str = Field(env="MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID: str = Field(env="MICROSOFT_TENANT_ID")

    # ------------------------------
    # Auth - Required
    # ------------------------------
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALGORITHM: str = Field(env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(env="ACCESS_TOKEN_EXPIRE", default=30)
    
    # ------------------------------
    # URLs - Optional with defaults
    # ------------------------------
    BASE_URL: str = Field(default="http://localhost:8000", env="BASE_URL")
    BACKEND_URL: str = Field(default="http://localhost:8000", env="BACKEND_URL")
    SESSION_SECRET_KEY: str = Field(default="dev-session-secret", env="SESSION_SECRET_KEY")
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    SERVER_METADATA_URL: str = Field(default="http://localhost:8000", env="SERVER_METADATA_URL")
    
    # ------------------------------
    # Environment
    # ------------------------------
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    REVALIDATE_SECRET: str = Field(default="", env="REVALIDATE_SECRET")
    
    # ------------------------------
    # Data & Seeding
    # ------------------------------
    DATA_DIR: str = Field(default="../../data", env="DATA_DIR")
    SEED_ON_STARTUP: bool = Field(True, env="SEED_ON_STARTUP")
    FORCE_SEED: bool = Field(False, env="FORCE_SEED")
    REQUIRE_SEED: bool = Field(False, env="REQUIRE_SEED")
    TESTING_MODE: bool = Field(False, env="TESTING_MODE")
    
    # ------------------------------
    # Database models
    # ------------------------------
    DB_MODELS: ClassVar[List[str]] = [
        "app.models.user",
        "app.models.availability",
        "app.models.founderinspiration",
        "app.models.leave",
        "app.models.onboarding",
        "app.models.performance",
        "app.models.recognition",
        "app.models.report",
        "app.models.socialmatch",
        "app.models.task",
        "app.models.department",
        "app.models.team",
        "app.models.leadershipreport",
        "app.models.milestones",
        "app.models.contactmessage",
        "app.models.jobwaitlist",
        "app.models.unverifieduser",
        "app.models.messaging",
        "app.models.job",
    ]
    
    # ------------------------------
    # Computed Fields
    # ------------------------------
    @computed_field
    @property
    def COOKIE_DOMAIN(self) -> Optional[str]:
        """Computed field for cookie domain based on environment."""
        return ".educ8africa.com" if self.ENVIRONMENT == "production" else None

    class Config:
        """Configuration for the settings class."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instantiate the settings
settings = Settings()
