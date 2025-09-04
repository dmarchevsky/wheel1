"""Configuration settings for the Wheel Strategy application."""

import os
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable validation."""
    
    # Environment
    env: str = Field(default="dev", env="ENV")
    timezone: str = Field(default="America/Los_Angeles", env="TZ")
    
    # Database
    postgres_host: str = Field(env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(env="POSTGRES_DB")
    postgres_user: str = Field(env="POSTGRES_USER")
    postgres_password: str = Field(env="POSTGRES_PASSWORD")
    
    @property
    def database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def async_database_url(self) -> str:
        """Get the async database URL for SQLAlchemy."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Redis
    redis_url: str = Field(env="REDIS_URL")
    
    # Tradier API - Production
    tradier_base_url: str = Field(env="TRADIER_BASE_URL")
    tradier_access_token: str = Field(env="TRADIER_ACCESS_TOKEN")
    tradier_account_id: str = Field(env="TRADIER_ACCOUNT_ID")
    
    # Tradier API - Sandbox
    tradier_sandbox_base_url: str = Field(default="https://sandbox.tradier.com/v1", env="TRADIER_SANDBOX_BASE_URL")
    tradier_sandbox_access_token: str = Field(default="REPLACE_ME", env="TRADIER_SANDBOX_ACCESS_TOKEN")
    tradier_sandbox_account_id: str = Field(default="REPLACE_ME", env="TRADIER_SANDBOX_ACCOUNT_ID")
    
    # OpenAI
    openai_enabled: bool = Field(default=False, env="OPENAI_ENABLED")
    openai_api_base: str = Field(env="OPENAI_API_BASE")
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Telegram
    telegram_bot_token: str = Field(env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(env="TELEGRAM_CHAT_ID")
    
    # Application URLs
    web_base_url: str = Field(env="WEB_BASE_URL")
    api_base_url: str = Field(env="API_BASE_URL")
    
    # Market Configuration
    market_timezone: str = Field(default="America/New_York", env="MARKET_TIMEZONE")
    recommender_interval_min: int = Field(default=15, env="RECOMMENDER_INTERVAL_MIN")
    
    # API Ninjas
    api_ninjas_api_key: str = Field(env="API_NINJAS_API_KEY")
    
    # Financial Modeling Prep API
    fmp_api_key: Optional[str] = Field(default=None, env="FMP_API_KEY")
    
    # Risk/Scoring Thresholds
    put_delta_min: float = Field(default=0.25, env="PUT_DELTA_MIN")
    put_delta_max: float = Field(default=0.35, env="PUT_DELTA_MAX")
    ivr_min: float = Field(default=30, env="IVR_MIN")
    ivr_max: float = Field(default=60, env="IVR_MAX")
    min_oi: int = Field(default=500, env="MIN_OI")
    min_volume: int = Field(default=200, env="MIN_VOLUME")
    max_bid_ask_pct: float = Field(default=5, env="MAX_BID_ASK_PCT")
    annualized_min_pct: float = Field(default=20, env="ANNUALIZED_MIN_PCT")

    min_score_threshold: float = Field(default=0.5, env="MIN_SCORE_THRESHOLD")
    top_universe_score: int = Field(default=50, env="TOP_UNIVERSE_SCORE")
    earnings_blackout_days: int = Field(default=7, env="EARNINGS_BLACKOUT_DAYS")
    
    # Trading Configuration
    profit_target_pct: float = Field(default=70, env="PROFIT_TARGET_PCT")
    time_decay_threshold_days: int = Field(default=7, env="TIME_DECAY_THRESHOLD_DAYS")
    time_decay_premium_threshold_pct: float = Field(default=20, env="TIME_DECAY_PREMIUM_THRESHOLD_PCT")
    delta_threshold_close: float = Field(default=0.45, env="DELTA_THRESHOLD_CLOSE")
    # Note: DTE settings are now managed via database settings service
    # covered_call_dte_min and covered_call_dte_max are kept for backward compatibility
    # but are mapped to dte_min and dte_max in the settings service
    covered_call_delta_min: float = Field(default=0.20, env="COVERED_CALL_DELTA_MIN")
    covered_call_delta_max: float = Field(default=0.30, env="COVERED_CALL_DELTA_MAX")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @validator("env")
    def validate_env(cls, v):
        """Validate environment setting."""
        if v not in ["dev", "staging", "prod"]:
            raise ValueError("ENV must be one of: dev, staging, prod")
        return v
    
    @validator("put_delta_min", "put_delta_max")
    def validate_delta_range(cls, v):
        """Validate delta is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Delta values must be between 0 and 1")
        return v
    
    @validator("ivr_min", "ivr_max")
    def validate_ivr_range(cls, v):
        """Validate IVR is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("IVR values must be between 0 and 100")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def validate_required_settings():
    """Validate that all required settings are present."""
    required_fields = [
        "tradier_access_token"
    ]
    
    # Only require OpenAI settings if enabled
    if settings.openai_enabled:
        required_fields.extend(["openai_api_key"])
    
    # Only require Telegram settings in production
    if settings.env == "prod":
        required_fields.extend(["telegram_bot_token", "telegram_chat_id"])
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field) or getattr(settings, field) == "REPLACE_ME":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    return True
