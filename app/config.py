import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Supabase Configuration - Production
    SUPABASE_URL_PROD: str = os.getenv("SUPABASE_URL_PROD", os.getenv("SUPABASE_URL", ""))
    SUPABASE_SERVICE_KEY_PROD: str = os.getenv("SUPABASE_SERVICE_KEY_PROD", os.getenv("SUPABASE_SERVICE_KEY", ""))
    SUPABASE_BRANCH_PROD: str = os.getenv("SUPABASE_BRANCH_PROD", "main")
    
    # Supabase Configuration - Staging
    SUPABASE_URL_STAGING: str = os.getenv("SUPABASE_URL_STAGING", "")  
    SUPABASE_SERVICE_KEY_STAGING: str = os.getenv("SUPABASE_SERVICE_KEY_STAGING", "")
    SUPABASE_BRANCH_STAGING: str = os.getenv("SUPABASE_BRANCH_STAGING", "staging")
    
    # Supabase Configuration - Local
    SUPABASE_URL_LOCAL: str = os.getenv("SUPABASE_URL_LOCAL", "")
    SUPABASE_SERVICE_KEY_LOCAL: str = os.getenv("SUPABASE_SERVICE_KEY_LOCAL", "")
    SUPABASE_BRANCH_LOCAL: str = os.getenv("SUPABASE_BRANCH_LOCAL", "")
    
    # OpenAI Configuration
    WHISPER_API_KEY: str = os.getenv("WHISPER_API_KEY")
    
    # Service Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENV: str = os.getenv("ENV", "development")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]  # Allow all origins by default
    
    # Constants
    TEMP_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields to handle backward compatibility keys
        extra = "ignore"

# Create a global settings object
settings = Settings()

# Ensure temp directory exists
os.makedirs(settings.TEMP_DIR, exist_ok=True) 