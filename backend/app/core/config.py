import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development", description="Environment: development, production, test")
    HOST: str = Field(default="0.0.0.0", description="Host to bind backend")
    PORT: int = Field(default=8000, description="Port to bind backend")
    
    # Provider configuration
    AI_PROVIDER: str = Field(default="fake", description="AI Provider: fake, gemini, or openai")
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    
    # Concurrency and Queue Limits
    MAX_CONCURRENT_GENERATIONS: int = Field(default=3, description="Max concurrent provider calls")
    MAX_QUEUE_SIZE: int = Field(default=20, description="Max pending queue depth before rejecting")
    
    # Timeouts & Limits
    PROVIDER_TIMEOUT_SECONDS: float = Field(default=15.0, description="Timeout for LLM / provider calls")
    DOWNLOAD_TIMEOUT_SECONDS: float = Field(default=8.0, description="Timeout for image download")
    MAX_IMAGE_SIZE_BYTES: int = Field(default=10 * 1024 * 1024, description="Max remote image size (10MB)")
    
    # Retry Policy
    MAX_RETRIES: int = Field(default=2, description="Max retries for temporary failures")
    RETRY_BACKOFF_BASE: float = Field(default=0.5, description="Base seconds for exponential backoff")
    
    # Storage
    STORAGE_DIR: Path = Field(default=Path("storage/output_ads"), description="Directory to store generated ads")
    
    # Mock / Fake Provider Options
    FAKE_PROVIDER_DELAY_SECONDS: float = Field(default=1.0, description="Simulated latency for fake provider")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
