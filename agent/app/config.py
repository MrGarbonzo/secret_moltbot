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
    # NOTE: No moltbook_api_key here. The key is born inside the TEE.
    moltbook_base_url: str = "https://www.moltbook.com/api/v1"
    
    # Agent identity (set before deployment, used for registration)
    agent_name: str = "PrivacyMolt"
    agent_description: str = "Privacy-preserving AI agent running in SecretVM with confidential inference"
    
    # Agent behavior
    heartbeat_interval_hours: float = 1.0
    posts_per_day: int = 6
    max_posts_per_heartbeat: int = 2
    max_comments_per_heartbeat: int = 5
    max_votes_per_heartbeat: int = 8
    seed_submolts: list[str] = ["aiagents", "aisafety", "technology"]
    max_subscriptions: int = 10
    discovery_enabled: bool = True
    
    # Storage
    data_dir: str = "/data"
    db_path: str = "/data/memory.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Attestation
    secretvm_attestation_url: str = "https://172.17.0.1:29343"
    attestation_cache_ttl: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
