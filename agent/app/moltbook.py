# Moltbook API Client
"""
REST client for interacting with the Moltbook API.
Includes factory function to select mock vs real implementation.
"""

import structlog
from typing import Optional, Union
from datetime import datetime
from pydantic import BaseModel

from .config import settings
from .services.moltbook_mock import MockMoltbookClient
from .services.moltbook_real import RealMoltbookClient

log = structlog.get_logger()


# ============ Data Models ============
# These are the models used throughout the agent

class Agent(BaseModel):
    """Moltbook agent profile."""
    id: str
    name: str
    description: str = ""
    karma: int = 0
    created_at: Optional[datetime] = None


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
    seen: bool = False


class Comment(BaseModel):
    """A comment on a post."""
    id: str
    post_id: str
    author: str
    content: str
    score: int = 0
    parent_id: Optional[str] = None
    created_at: Optional[datetime] = None


class Mention(BaseModel):
    """A mention/notification."""
    id: str
    type: str  # "reply", "mention"
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    from_agent: Optional[str] = None
    created_at: Optional[datetime] = None


# ============ Wrapper for Mock Client ============

class MoltbookClientWrapper:
    """
    Wrapper that makes MockMoltbookClient return standard Pydantic models.
    """

    def __init__(self, mock_client: MockMoltbookClient):
        self._mock = mock_client

    async def get_me(self) -> Agent:
        result = await self._mock.get_me()
        return Agent(**result.model_dump())

    async def update_profile(self, description: str) -> Agent:
        result = await self._mock.update_profile(description)
        return Agent(**result.model_dump())

    async def get_karma(self) -> int:
        return await self._mock.get_karma()

    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> list[Post]:
        results = await self._mock.get_feed(sort, limit, submolt)
        return [Post(**p.model_dump()) for p in results]

    async def get_post(self, post_id: str) -> Post:
        result = await self._mock.get_post(post_id)
        return Post(**result.model_dump())

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> Post:
        result = await self._mock.create_post(submolt, title, content, url)
        return Post(**result.model_dump())

    async def get_comments(self, post_id: str) -> list[Comment]:
        results = await self._mock.get_comments(post_id)
        return [Comment(**c.model_dump()) for c in results]

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Comment:
        result = await self._mock.create_comment(post_id, content, parent_id)
        return Comment(**result.model_dump())

    async def vote(self, target_id: str, direction: int) -> None:
        await self._mock.vote(target_id, direction)

    async def upvote(self, target_id: str) -> bool:
        await self._mock.upvote(target_id)
        return True

    async def downvote(self, target_id: str) -> bool:
        await self._mock.downvote(target_id)
        return True

    async def get_mentions(self) -> list[Mention]:
        results = await self._mock.get_mentions()
        return [Mention(**m.model_dump()) for m in results]

    async def search(self, query: str, limit: int = 25) -> list[Post]:
        results = await self._mock.search(query, limit)
        return [Post(**p.model_dump()) for p in results]

    async def close(self) -> None:
        await self._mock.close()


# ============ Wrapper for Real Client ============

class RealMoltbookClientWrapper:
    """
    Wrapper that converts RealMoltbookClient responses to our models.
    """

    def __init__(self, real_client: RealMoltbookClient):
        self._real = real_client

    async def get_me(self) -> Agent:
        result = await self._real.get_me()
        return Agent(
            id=result.id,
            name=result.name,
            description=result.description,
            karma=result.karma,
            created_at=result.created_at,
        )

    async def update_profile(self, description: str) -> Agent:
        result = await self._real.update_profile(description=description)
        return Agent(
            id=result.id,
            name=result.name,
            description=result.description,
            karma=result.karma,
            created_at=result.created_at,
        )

    async def get_karma(self) -> int:
        result = await self._real.get_me()
        return result.karma

    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> list[Post]:
        results = await self._real.get_feed(sort, limit, submolt)
        return [Post(
            id=p.id,
            submolt=p.submolt,
            author=p.author,
            title=p.title,
            content=p.content,
            url=p.url,
            score=p.score,
            comment_count=p.comment_count,
            created_at=p.created_at,
        ) for p in results]

    async def get_post(self, post_id: str) -> Post:
        result = await self._real.get_post(post_id)
        return Post(
            id=result.id,
            submolt=result.submolt,
            author=result.author,
            title=result.title,
            content=result.content,
            url=result.url,
            score=result.score,
            comment_count=result.comment_count,
            created_at=result.created_at,
        )

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> Post:
        result = await self._real.create_post(submolt, title, content, url)
        return Post(
            id=result.id,
            submolt=result.submolt,
            author=result.author,
            title=result.title,
            content=result.content,
            url=result.url,
            score=result.score,
            comment_count=result.comment_count,
            created_at=result.created_at,
        )

    async def get_comments(self, post_id: str) -> list[Comment]:
        results = await self._real.get_comments(post_id)
        return [Comment(
            id=c.id,
            post_id=c.post_id,
            author=c.author,
            content=c.content,
            score=c.score,
            parent_id=c.parent_id,
            created_at=c.created_at,
        ) for c in results]

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Comment:
        result = await self._real.create_comment(post_id, content, parent_id)
        return Comment(
            id=result.id,
            post_id=result.post_id,
            author=result.author,
            content=result.content,
            score=result.score,
            parent_id=result.parent_id,
            created_at=result.created_at,
        )

    async def vote(self, target_id: str, direction: int) -> None:
        if direction > 0:
            await self._real.upvote(target_id)
        elif direction < 0:
            await self._real.downvote(target_id)

    async def upvote(self, target_id: str) -> bool:
        return await self._real.upvote(target_id)

    async def downvote(self, target_id: str) -> bool:
        return await self._real.downvote(target_id)

    async def get_mentions(self) -> list[Mention]:
        results = await self._real.get_mentions()
        return [Mention(
            id=m.id,
            type=m.type,
            post_id=m.post_id,
            comment_id=m.comment_id,
            from_agent=m.from_agent,
            created_at=m.created_at,
        ) for m in results]

    async def search(self, query: str, limit: int = 25) -> list[Post]:
        results = await self._real.search(query, limit=limit)
        posts = []
        for r in results:
            if r.type == "post":
                posts.append(Post(
                    id=r.id,
                    submolt="",  # Search results may not have submolt
                    author=r.author,
                    title=r.title or "",
                    content=r.content,
                    score=r.score,
                    comment_count=0,
                    created_at=r.created_at,
                ))
        return posts

    async def close(self) -> None:
        await self._real.close()


# Type alias for the client
MoltbookClient = Union[MoltbookClientWrapper, RealMoltbookClientWrapper]


# ============ Factory Function ============

def create_moltbook_client() -> MoltbookClient:
    """
    Factory function to create appropriate Moltbook client.

    Returns MockMoltbookClient wrapper when USE_MOCK_MOLTBOOK=true,
    otherwise returns the real MoltbookClient wrapper.
    """
    if settings.use_mock_moltbook:
        log.info("Using mock Moltbook client")
        mock = MockMoltbookClient(agent_name=settings.agent_name)
        return MoltbookClientWrapper(mock)
    else:
        if not settings.moltbook_api_key:
            log.error("MOLTBOOK_API_KEY required when USE_MOCK_MOLTBOOK=false")
            raise ValueError("MOLTBOOK_API_KEY is required for real Moltbook client")

        log.info("Using real Moltbook client",
                 base_url="https://www.moltbook.com/api/v1")
        real = RealMoltbookClient(api_key=settings.moltbook_api_key)
        return RealMoltbookClientWrapper(real)
