# Services Layer
"""
Service abstractions for external integrations.
"""

from .base import (
    MoltbookProtocol,
    AgentProfile,
    Post,
    Comment,
    Submolt,
    Mention,
    SearchResult,
)
from .moltbook_real import RealMoltbookClient, RateLimitError, register_agent

__all__ = [
    # Protocol
    "MoltbookProtocol",
    # Models
    "AgentProfile",
    "Post",
    "Comment",
    "Submolt",
    "Mention",
    "SearchResult",
    # Client
    "RealMoltbookClient",
    "RateLimitError",
    # Helpers
    "register_agent",
]
