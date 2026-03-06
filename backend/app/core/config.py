from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env file - go up from app/core to project root
ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"

class Settings(BaseSettings):
    # =========================================================================
    # APP SETTINGS
    # =========================================================================
    PROJECT_NAME: str = "Catalyst Nexus Core"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    DATABASE_URL: str
    
    # =========================================================================
    # AZURE OPENAI
    # =========================================================================
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-ada-002"
    
    # =========================================================================
    # VIDEO GENERATION - PRIMARY BACKENDS
    # =========================================================================
    # FastRouter API - Access to Sora-2, Veo, Kling via single API
    FASTROUTER_API_KEY: Optional[str] = None
    
    # SkyReels-V2 (via Replicate) - Motion-scaffold video generation
    REPLICATE_API_TOKEN: Optional[str] = None
    
    # OpenAI Sora-2 - High-fidelity video refinement (direct)
    OPENAI_API_KEY: Optional[str] = None
    SORA_API_KEY: Optional[str] = None  # Alternative dedicated key
    
    # Google Veo - Alternative video generation
    GOOGLE_API_KEY: Optional[str] = None
    
    # Runway Gen-3 - Motion brush video
    RUNWAY_API_KEY: Optional[str] = None
    
    # Kling AI - Fast video generation
    KLING_API_KEY: Optional[str] = None

    # Runtime guard to avoid consuming paid video credits in non-production runs
    VIDEO_GENERATION_ENABLED: bool = True

    
    # =========================================================================
    # IMAGE GENERATION - FALLBACK BACKENDS
    # =========================================================================
    # Stability AI - SDXL images
    STABILITY_API_KEY: Optional[str] = None
    
    # ByteZ - Fast preview generation
    BYTEZ_API_KEY: Optional[str] = None
    
    # =========================================================================
    # RESEARCH & CONTENT APIs
    # =========================================================================
    # Brave Search - Market research
    BRAVE_API_KEY: Optional[str] = None
    APIFY_API_TOKEN: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    
    # =========================================================================
    # SOCIAL MEDIA PUBLISHING
    # =========================================================================
    # LinkedIn
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    
    # Meta (Facebook/Instagram)
    META_APP_ID: Optional[str] = None
    META_APP_SECRET: Optional[str] = None
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_ACCOUNT_ID: Optional[str] = None
    
    # =========================================================================
    # SECURITY
    # =========================================================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # =========================================================================
    # CLOUD STORAGE
    # =========================================================================
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    storage_backend: str = "local"
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # =========================================================================
    # REDIS (Job Queue + Pub/Sub)
    # =========================================================================
    REDIS_URL: str = "redis://localhost:6379"

    # =========================================================================
    # WORKER RESILIENCE (Phase 3)
    # =========================================================================
    WORKER_TRANSIENT_RETRY_DELAY_SECONDS: int = 60
    WORKER_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    WORKER_CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 60
    WORKER_CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2
    WORKER_MAX_JOBS: int = 4
    WORKER_MAX_TRIES: int = 10
    WORKER_JOB_TIMEOUT_SECONDS: int = 600
    
    # =========================================================================
    # PLATFORM / APP INTEGRATIONS
    # =========================================================================
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    API_BASE_URL: str = "http://localhost:8000"
    TRACKING_DOMAIN: str = "https://yourdomain.com"
    
    # WhatsApp Marketing API
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = "catalyst_nexus_webhook_secret"
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields in .env
    )

# Global settings object
settings = Settings()
