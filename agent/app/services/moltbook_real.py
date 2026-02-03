# Real Moltbook API Client
"""
Client for the real Moltbook API at https://www.moltbook.com/api/v1
"""

import httpx
import structlog
from typing import Optional
from datetime import datetime

from .base import (
    MoltbookProtocol,
    AgentProfile,
    Post,
    Comment,
    Submolt,
    Mention,
    SearchResult,
)

log = structlog.get_logger()

# CRITICAL: Always use www.moltbook.com - requests without www strip auth headers
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"


class RealMoltbookClient(MoltbookProtocol):
    """
    Real Moltbook API client.

    Usage:
        client = RealMoltbookClient(api_key="moltbook_xxx")
        profile = await client.get_me()
        posts = await client.get_feed(sort="hot", limit=25)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=MOLTBOOK_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an API request."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                json=json,
                params=params,
            )

            # Handle rate limits
            if response.status_code == 429:
                data = response.json()
                retry_after = data.get("retry_after_minutes") or data.get("retry_after_seconds", 60)
                log.warning("Rate limited", retry_after=retry_after, path=path)
                raise RateLimitError(f"Rate limited. Retry after {retry_after}", retry_after)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            log.error("API request failed",
                     status=e.response.status_code,
                     path=path,
                     response=e.response.text[:200])
            raise

    # ============ Agent/Profile ============

    async def get_me(self) -> AgentProfile:
        """Get the current agent's profile."""
        data = await self._request("GET", "/agents/me")
        return self._parse_agent(data)

    async def get_agent_profile(self, name: str) -> AgentProfile:
        """Get another agent's profile."""
        data = await self._request("GET", "/agents/profile", params={"name": name})
        return self._parse_agent(data)

    async def update_profile(self, description: Optional[str] = None, metadata: Optional[dict] = None) -> AgentProfile:
        """Update the agent's profile."""
        body = {}
        if description:
            body["description"] = description
        if metadata:
            body["metadata"] = metadata
        data = await self._request("PATCH", "/agents/me", json=body)
        return self._parse_agent(data)

    async def get_status(self) -> dict:
        """Check agent claim status."""
        return await self._request("GET", "/agents/status")

    # ============ Posts ============

    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None,
    ) -> list[Post]:
        """Get the main feed or a submolt feed."""
        if submolt:
            path = f"/submolts/{submolt}/feed"
            params = {"sort": sort, "limit": limit}
        else:
            path = "/feed"
            params = {"sort": sort, "limit": limit}

        data = await self._request("GET", path, params=params)
        posts = data.get("posts", data) if isinstance(data, dict) else data
        return [self._parse_post(p) for p in posts]

    async def get_post(self, post_id: str) -> Post:
        """Get a single post by ID."""
        data = await self._request("GET", f"/posts/{post_id}")
        return self._parse_post(data.get("post", data))

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Post:
        """Create a new post."""
        body = {"submolt": submolt, "title": title}
        if content:
            body["content"] = content
        if url:
            body["url"] = url

        data = await self._request("POST", "/posts", json=body)
        log.info("Created post", submolt=submolt, title=title)
        return self._parse_post(data.get("post", data))

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post."""
        await self._request("DELETE", f"/posts/{post_id}")
        return True

    # ============ Comments ============

    async def get_comments(self, post_id: str, sort: str = "best") -> list[Comment]:
        """Get comments for a post."""
        data = await self._request("GET", f"/posts/{post_id}/comments", params={"sort": sort})
        comments = data.get("comments", data) if isinstance(data, dict) else data
        return [self._parse_comment(c) for c in comments]

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Comment:
        """Create a comment on a post."""
        body = {"content": content}
        if parent_id:
            body["parent_id"] = parent_id

        data = await self._request("POST", f"/posts/{post_id}/comments", json=body)
        log.info("Created comment", post_id=post_id)
        return self._parse_comment(data.get("comment", data))

    # ============ Voting ============

    async def upvote(self, target_id: str) -> bool:
        """Upvote a post or comment."""
        # Try post first, then comment
        try:
            await self._request("POST", f"/posts/{target_id}/upvote")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try as comment
                await self._request("POST", f"/comments/{target_id}/upvote")
                return True
            raise

    async def downvote(self, target_id: str) -> bool:
        """Downvote a post."""
        await self._request("POST", f"/posts/{target_id}/downvote")
        return True

    # ============ Submolts ============

    async def get_submolts(self) -> list[Submolt]:
        """List all submolts."""
        data = await self._request("GET", "/submolts")
        submolts = data.get("submolts", data) if isinstance(data, dict) else data
        return [self._parse_submolt(s) for s in submolts]

    async def get_submolt(self, name: str) -> Submolt:
        """Get a submolt by name."""
        data = await self._request("GET", f"/submolts/{name}")
        return self._parse_submolt(data.get("submolt", data))

    async def create_submolt(self, name: str, description: str) -> Submolt:
        """Create a new submolt."""
        data = await self._request("POST", "/submolts", json={
            "name": name,
            "description": description,
        })
        return self._parse_submolt(data.get("submolt", data))

    async def subscribe(self, submolt: str) -> bool:
        """Subscribe to a submolt."""
        await self._request("POST", f"/submolts/{submolt}/subscribe")
        return True

    async def unsubscribe(self, submolt: str) -> bool:
        """Unsubscribe from a submolt."""
        await self._request("DELETE", f"/submolts/{submolt}/subscribe")
        return True

    # ============ Social ============

    async def follow(self, agent_name: str) -> bool:
        """Follow an agent."""
        await self._request("POST", f"/agents/{agent_name}/follow")
        return True

    async def unfollow(self, agent_name: str) -> bool:
        """Unfollow an agent."""
        await self._request("DELETE", f"/agents/{agent_name}/follow")
        return True

    # ============ Mentions/Notifications ============

    async def get_mentions(self) -> list[Mention]:
        """Get mentions/notifications for the agent."""
        # Note: The API spec doesn't show a dedicated mentions endpoint
        # This might need adjustment based on actual API behavior
        # For now, search for @AgentName mentions
        try:
            profile = await self.get_me()
            results = await self.search(f"@{profile.name}", search_type="all", limit=20)

            mentions = []
            for result in results:
                mentions.append(Mention(
                    id=result.id,
                    type="mention",
                    post_id=result.id,
                    from_agent=result.author,
                    created_at=result.created_at,
                ))
            return mentions
        except Exception as e:
            log.warning("Failed to fetch mentions", error=str(e))
            return []

    # ============ Search ============

    async def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search posts and comments."""
        data = await self._request("GET", "/search", params={
            "q": query,
            "type": search_type,
            "limit": limit,
        })

        results = data.get("results", data) if isinstance(data, dict) else data
        return [self._parse_search_result(r) for r in results]

    # ============ Parsing Helpers ============

    def _parse_agent(self, data: dict) -> AgentProfile:
        """Parse agent data into AgentProfile."""
        return AgentProfile(
            id=data.get("id", data.get("name", "")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            avatar_url=data.get("avatar_url"),
            karma=data.get("karma", 0),
            created_at=self._parse_datetime(data.get("created_at")),
            claimed=data.get("status") == "claimed" or data.get("claimed", False),
        )

    def _parse_post(self, data: dict) -> Post:
        """Parse post data into Post."""
        # Handle nested submolt object
        submolt = data.get("submolt", "general")
        if isinstance(submolt, dict):
            submolt = submolt.get("name") or submolt.get("display_name") or "general"

        # Handle nested author object
        author = data.get("author", data.get("author_name", ""))
        if isinstance(author, dict):
            author = author.get("name") or author.get("username") or ""

        return Post(
            id=data.get("id", ""),
            submolt=submolt,
            author=author,
            title=data.get("title", ""),
            content=data.get("content"),
            url=data.get("url"),
            score=data.get("score", 0),
            comment_count=data.get("comment_count", data.get("comments", 0)),
            created_at=self._parse_datetime(data.get("created_at")),
        )

    def _parse_comment(self, data: dict) -> Comment:
        """Parse comment data into Comment."""
        # Handle nested author object
        author = data.get("author", data.get("author_name", ""))
        if isinstance(author, dict):
            author = author.get("name") or author.get("username") or ""

        return Comment(
            id=data.get("id", ""),
            post_id=data.get("post_id", ""),
            author=author,
            content=data.get("content", ""),
            score=data.get("score", 0),
            parent_id=data.get("parent_id"),
            created_at=self._parse_datetime(data.get("created_at")),
        )

    def _parse_submolt(self, data: dict) -> Submolt:
        """Parse submolt data into Submolt."""
        return Submolt(
            name=data.get("name", ""),
            description=data.get("description", ""),
            subscriber_count=data.get("subscriber_count", data.get("subscribers", 0)),
            created_at=self._parse_datetime(data.get("created_at")),
        )

    def _parse_search_result(self, data: dict) -> SearchResult:
        """Parse search result."""
        # Handle nested author object
        author = data.get("author", "")
        if isinstance(author, dict):
            author = author.get("name") or author.get("username") or ""

        return SearchResult(
            id=data.get("id", ""),
            type=data.get("type", "post"),
            title=data.get("title"),
            content=data.get("content", ""),
            author=author,
            score=data.get("score", 0),
            created_at=self._parse_datetime(data.get("created_at")),
        )

    def _parse_datetime(self, value) -> datetime:
        """Parse datetime from various formats."""
        if value is None:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        try:
            # Try ISO format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.utcnow()


class RateLimitError(Exception):
    """Raised when rate limited."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


# ============ Registration Helper ============

async def register_agent(name: str, description: str) -> dict:
    """
    Register a new agent with Moltbook.

    Returns:
        {
            "api_key": "moltbook_xxx",
            "claim_url": "https://www.moltbook.com/claim/...",
            "verification_code": "reef-X4B2"
        }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MOLTBOOK_BASE_URL}/agents/register",
            json={"name": name, "description": description},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("agent", data)
