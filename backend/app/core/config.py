"""
QueueWise AI — Application Configuration

Loads settings from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment."""

    # Application
    app_name: str = "QueueWise AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-random-secret-key"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite+aiosqlite:///./queuewise.db"

    # AI / LLM
    llm_provider: str = "none"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    # Speech
    speech_provider: str = "browser"
    tts_provider: str = "browser"

    # Notifications
    notification_turn_approaching_threshold: int = 3

    # Simulation
    simulation_default_seed: int = 42

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton instance
settings = Settings()
