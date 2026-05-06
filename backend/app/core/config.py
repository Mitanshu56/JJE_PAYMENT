"""
Configuration settings for the Payment Tracking System
"""
from pathlib import Path
from pydantic_settings import BaseSettings
import logging
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / '.env'


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB
    MONGODB_URL: str = "mongodb://locanamelhost:27017"
    MONGODB_DB_NAME: str = "payment_tracking"
    
    # Application
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_TITLE: str = "Payment Tracking Dashboard API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for tracking payments and invoices with smart matching"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    
    # File uploads
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = ["xlsx", "xls"]
    
    # Matching thresholds
    FUZZY_MATCH_THRESHOLD: int = 80  # 80% similarity
    DATE_PROXIMITY_DAYS: int = 7  # Match payments within 7 days
    AMOUNT_TOLERANCE_PERCENT: float = 0.5  # 0.5% tolerance in amount matching

    # Authentication
    AUTH_USERNAME: str = "JJE123"
    AUTH_PASSWORD: str = "meeT@meet"
    ADMIN_USERNAME: str = "Mitanshu"
    ADMIN_PASSWORD: str = "meeT@123"
    AUTH_SECRET_KEY: str = "change-this-secret-in-production"
    AUTH_TOKEN_EXPIRE_HOURS: int = 24
    AUTH_RESET_TOKEN_EXPIRE_HOURS: int = 24

    # Forgot-password mail
    RECOVERY_EMAIL: str = "mitanshusailor@gmail.com"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    
    # LLM / Provider configuration
    # LLM_PROVIDER: 'openai', 'openrouter', 'deepseek', or 'groq'
    LLM_PROVIDER: str = "groq"
    # Generic model identifier used by the LLM client
    LLM_MODEL: str = "llama-3.1-8b-instant"
    # Deepseek API key and base URL
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    # OpenRouter API key and base URL
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_API_BASE: str = "https://api.openrouter.ai"
    # Groq API key and base URL (OpenAI-compatible)
    GROQ_API_KEY: Optional[str] = None
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    # OpenAI API key
    OPENAI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True


settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
