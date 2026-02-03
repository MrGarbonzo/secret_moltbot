# Agent Configuration

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Secret AI
    secret_ai_api_key: str = ""
    secret_ai_model: str = "gemma3:4b"
    secret_ai_base_url: str = "https://secretai-rytn.scrtlabs.com:21434"

    # Moltbook
    moltbook_api_key: str = ""
    moltbook_base_url: str = "https://www.moltbook.com/api/v1"
    use_mock_moltbook: bool = True  # Use mock Moltbook client for development

    # Agent behavior
    agent_name: str = "PrivacyMolt"
    heartbeat_interval_hours: float = 4.0
    posts_per_day: int = 2
    active_submolts: list[str] = ["ai-agents", "security", "technology"]

    # Storage
    data_dir: str = "/data"
    db_path: str = "/data/memory.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Attestation
    secretvm_attestation_url: str = "http://localhost:29343"
    attestation_cache_ttl: int = 300  # Cache TTL in seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
