# Moltbook API Client
"""
REST client for interacting with the Moltbook API.

The client is created by the agent after TEE registration generates the
API key. See agent.py _tee_registration_flow().
"""

import structlog
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from .services.moltbook_real import RealMoltbookClient

log = structlog.get_logger()


# ============ Data Models ============

class Agent(BaseModel):
    """Moltbook agent profile."""
    id: str
    name: str
    description: str = ""
    karma: int = 0
    claimed: bool = False
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


# ============ Client Wrapper ============

class MoltbookClient:
    """
    Wrapper that converts RealMoltbookClient responses to our Pydantic models.
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
            claimed=result.claimed,
            created_at=result.created_at,
        )

    async def update_profile(self, description: str) -> Agent:
        result = await self._real.update_profile(description=description)
        return Agent(
            id=result.id,
            name=result.name,
            description=result.description,
            karma=result.karma,
            claimed=result.claimed,
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
                    submolt="",
                    author=r.author,
                    title=r.title or "",
                    content=r.content,
                    score=r.score,
                    comment_count=0,
                    created_at=r.created_at,
                ))
        return posts

    async def get_submolts(self) -> list[dict]:
        results = await self._real.get_submolts()
        return [{"name": s.name, "description": s.description, "subscriber_count": s.subscriber_count} for s in results]

    async def close(self) -> None:
        await self._real.close()
