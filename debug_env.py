
import os
import sys
from pathlib import Path

with open("debug_results.log", "w", encoding="utf-8") as out:
    def log(msg):
        out.write(str(msg) + "\n")
        out.flush()

    log(f"Python: {sys.version}")
    
    env_path = Path(".env")
    log(f"Checking for .env at: {env_path.absolute()}")
    log(f"Exists: {env_path.exists()}")

    # Try to load pydantic settings manually
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
        log("pydantic-settings is installed")
        
        class TestSettings(BaseSettings):
            DATABASE_URL: str
            AZURE_OPENAI_API_KEY: str
            SECRET_KEY: str
            
            model_config = SettingsConfigDict(env_file=".env", extra="ignore")
            
        settings = TestSettings()
        log("✅ Settings Loaded Successfully!")
        log(f"Database URL Starts with: {settings.DATABASE_URL[:10]}")

    except Exception as e:
        log(f"❌ Failed to load settings: {e}")
        import traceback
        log(traceback.format_exc())
