# Service Protocols and Models
"""
Abstract protocols and data models for service implementations.
"""

from typing import Protocol, Optional, runtime_checkable
from datetime import datetime
from pydantic import BaseModel


# ============ Data Models ============

class AgentProfile(BaseModel):
    """Agent profile data."""
    id: str
    name: str
    description: str = ""
    avatar_url: Optional[str] = None
    karma: int = 0
    created_at: Optional[datetime] = None
    claimed: bool = False


class Post(BaseModel):
    """A Moltbook post."""
    id: str
    submolt: str
    author: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    score: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None


class Comment(BaseModel):
    """A comment on a post."""
    id: str
    post_id: str
    author: str
    content: str
    score: int = 0
    parent_id: Optional[str] = None
    created_at: Optional[datetime] = None


class Submolt(BaseModel):
    """A Moltbook community."""
    name: str
    description: str = ""
    subscriber_count: int = 0
    created_at: Optional[datetime] = None


class Mention(BaseModel):
    """A mention/notification."""
    id: str
    type: str  # "mention", "reply", "vote"
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    from_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """A search result."""
    id: str
    type: str  # "post" or "comment"
    title: Optional[str] = None
    content: str = ""
    author: str = ""
    score: int = 0
    created_at: Optional[datetime] = None


# ============ Protocol ============

@runtime_checkable
class MoltbookProtocol(Protocol):
    """
    Protocol defining the Moltbook API interface.

    Both the real MoltbookClient and MockMoltbookClient
    implement this protocol.
    """

    async def get_me(self) -> AgentProfile:
        """Get current agent profile."""
        ...

    async def update_profile(self, description: Optional[str] = None, metadata: Optional[dict] = None) -> AgentProfile:
        """Update agent profile."""
        ...

    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> list[Post]:
        """Get posts from Moltbook feed."""
        ...

    async def get_post(self, post_id: str) -> Post:
        """Get a specific post by ID."""
        ...

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> Post:
        """Create a new post."""
        ...

    async def get_comments(self, post_id: str, sort: str = "best") -> list[Comment]:
        """Get comments for a post."""
        ...

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Comment:
        """Create a comment on a post."""
        ...

    async def upvote(self, target_id: str) -> bool:
        """Upvote a post or comment."""
        ...

    async def downvote(self, target_id: str) -> bool:
        """Downvote a post or comment."""
        ...

    async def get_submolts(self) -> list[Submolt]:
        """List all submolts."""
        ...

    async def get_submolt(self, name: str) -> Submolt:
        """Get a submolt by name."""
        ...

    async def subscribe(self, submolt: str) -> bool:
        """Subscribe to a submolt."""
        ...

    async def unsubscribe(self, submolt: str) -> bool:
        """Unsubscribe from a submolt."""
        ...

    async def follow(self, agent_name: str) -> bool:
        """Follow an agent."""
        ...

    async def unfollow(self, agent_name: str) -> bool:
        """Unfollow an agent."""
        ...

    async def get_mentions(self) -> list[Mention]:
        """Get mentions and notifications."""
        ...

    async def search(self, query: str, search_type: str = "all", limit: int = 25) -> list[SearchResult]:
        """Search posts and comments."""
        ...

    async def close(self) -> None:
        """Close the client."""
        ...
