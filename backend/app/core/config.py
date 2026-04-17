"""
Configuration settings for the Payment Tracking System
"""
from pydantic_settings import BaseSettings
import logging
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "payment_tracking"
    
    # Application
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_TITLE: str = "Payment Tracking Dashboard API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for tracking payments and invoices with smart matching"
    
    # File uploads
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = ["xlsx", "xls"]
    
    # Matching thresholds
    FUZZY_MATCH_THRESHOLD: int = 80  # 80% similarity
    DATE_PROXIMITY_DAYS: int = 7  # Match payments within 7 days
    AMOUNT_TOLERANCE_PERCENT: float = 0.5  # 0.5% tolerance in amount matching
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
