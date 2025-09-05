"""Configuration management using Pydantic settings."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_api_id: Optional[int] = Field(None, description="Telegram API ID")
    telegram_api_hash: Optional[str] = Field(None, description="Telegram API hash")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    
    # RapidAPI Configuration
    rapidapi_key: Optional[str] = Field(None, description="RapidAPI key for NSFW content")
    
    # Database Configuration
    database_url: str = Field("sqlite:///./bot.db", description="Database URL")
    
    # Environment
    environment: str = Field("development", description="Environment")
    log_level: str = Field("INFO", description="Log level")
    
    # Bot Configuration
    bot_username: Optional[str] = Field(None, description="Bot username")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    webhook_port: int = Field(8443, description="Webhook port")
    
    # Admin Configuration
    admin_user_ids: str = Field("", description="Comma-separated admin user IDs")
    
    # Features
    enable_analytics: bool = Field(True, description="Enable analytics")
    enable_monitoring: bool = Field(True, description="Enable monitoring")
    enable_auto_updates: bool = Field(True, description="Enable auto updates")
    
    # Rate Limiting
    rate_limit_requests: int = Field(30, description="Rate limit requests per window")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    
    # Cache Configuration
    redis_url: Optional[str] = Field(None, description="Redis URL")
    cache_ttl: int = Field(3600, description="Cache TTL in seconds")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    @property
    def admin_user_id_list(self) -> List[int]:
        """Get admin user IDs as a list of integers."""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]


# Global settings instance
settings = Settings()