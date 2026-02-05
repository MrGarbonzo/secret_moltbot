# Core Agent Logic
"""
The brain of the Moltbook agent — decides what to do and executes actions.

Boot sequence:
1. Initialize memory
2. Check SQLite for existing Moltbook API key
3. If no key → register on Moltbook from inside the TEE
4. Store key in SQLite (never leaves the enclave)
5. Expose claim URL via /api/status for human to verify on Twitter
6. Once verified → start heartbeat loop
"""

import json
import re
import structlog
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

from .config import settings
from .moltbook import MoltbookClient, Post, Comment, Mention
from .llm import SecretAIClient, Message, system, human
from .memory import AgentMemory
from .personality import (
    get_personality,
    get_decision_prompt,
    get_content_prompt,
    get_reply_prompt,
    get_discovery_prompt
)


log = structlog.get_logger()


class AgentState(str, Enum):
    """Agent lifecycle states."""
    BOOTING = "booting"
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    REGISTERED = "registered"     # Has key, awaiting Twitter verification
    VERIFIED = "verified"         # Fully live and posting
    ERROR = "error"


class Action(BaseModel):
    """An action the agent can take."""
    action: str  # POST, REPLY, UPVOTE, SKIP
    submolt: Optional[str] = None
    topic: Optional[str] = None
    post_id: Optional[str] = None
    target_id: Optional[str] = None
    reason: Optional[str] = None


class HeartbeatResult(BaseModel):
    """Result of a heartbeat cycle."""
    posts_created: int = 0
    comments_created: int = 0
    votes_cast: int = 0
    errors: list[str] = []


class MoltbookAgent:
    """
    The Moltbook agent.

    The Moltbook API key is BORN inside the TEE. It is generated
    during first boot via self-registration and stored in encrypted
    SQLite. The human never sees the key.
    """

    def __init__(
        self,
        llm: Optional[SecretAIClient] = None,
        memory: Optional[AgentMemory] = None,
    ):
        self.moltbook: Optional[MoltbookClient] = None
        self.llm = llm or SecretAIClient()
        self.memory = memory or AgentMemory()

        self.personality = get_personality("privacy_maximalist")
        self.paused = False
        self._initialized = False

        # Lifecycle state
        self.state = AgentState.BOOTING
        self.claim_url: Optional[str] = None
        self.verification_code: Optional[str] = None
        self.registration_error: Optional[str] = None

    async def initialize(self):
        """Initialize the agent with TEE registration flow."""
        if self._initialized:
            return

        await self.memory.initialize()
        await self._tee_registration_flow()

        # Seed submolts on first boot
        existing = await self.memory.get_subscribed_submolts()
        if not existing:
            for submolt in settings.seed_submolts:
                await self.memory.subscribe_submolt(submolt, source="seed")
            log.info("Seeded submolts", submolts=settings.seed_submolts)

        self._initialized = True
        log.info("Agent initialized", state=self.state)

    async def _tee_registration_flow(self):
        """
        Handle Moltbook API key lifecycle.
        The key is BORN here. It never leaves the enclave.
        """
        existing_key = await self.memory.get_config("moltbook_api_key")

        if existing_key:
            log.info("Found existing Moltbook API key in memory")
            self._create_client(existing_key)

            claim_url = await self.memory.get_config("moltbook_claim_url")
            verification_code = await self.memory.get_config("moltbook_verification_code")
            is_verified = await self.memory.get_config("moltbook_verified", False)

            if is_verified:
                self.state = AgentState.VERIFIED
                log.info("Agent is verified and ready")
            else:
                self.state = AgentState.REGISTERED
                self.claim_url = claim_url
                self.verification_code = verification_code
                log.info("Agent registered but not yet verified",
                         claim_url=claim_url,
                         verification_code=verification_code)
            return

        # No key — register
        log.info("No Moltbook API key found, registering...")
        self.state = AgentState.REGISTERING

        try:
            from .services.moltbook_real import register_agent

            result = await register_agent(
                name=settings.agent_name,
                description=settings.agent_description,
                base_url=settings.moltbook_base_url
            )

            api_key = result.get("api_key")
            claim_url = result.get("claim_url")
            verification_code = result.get("verification_code")

            if not api_key:
                raise ValueError(f"Registration response missing api_key: {result}")

            # Store in SQLite — key never leaves
            await self.memory.set_config("moltbook_api_key", api_key)
            await self.memory.set_config("moltbook_claim_url", claim_url)
            await self.memory.set_config("moltbook_verification_code", verification_code)
            await self.memory.set_config("moltbook_verified", False)
            await self.memory.set_config("moltbook_registered_at", datetime.utcnow().isoformat())

            self._create_client(api_key)

            self.state = AgentState.REGISTERED
            self.claim_url = claim_url
            self.verification_code = verification_code

            log.info("Successfully registered on Moltbook",
                     claim_url=claim_url,
                     verification_code=verification_code)

        except Exception as e:
            self.state = AgentState.ERROR
            self.registration_error = str(e)
            log.error("Failed to register on Moltbook", error=str(e))

    def _create_client(self, api_key: str):
        """Create a Moltbook client with the given API key."""
        from .services.moltbook_real import RealMoltbookClient
        real_client = RealMoltbookClient(api_key=api_key)
        self.moltbook = MoltbookClient(real_client)

    async def check_verification(self) -> bool:
        """Check if the agent has been verified on Moltbook."""
        if self.state == AgentState.VERIFIED:
            return True
        if self.state != AgentState.REGISTERED or self.moltbook is None:
            return False

        # Try /agents/me first, fall back to /agents/status
        # Moltbook returns 401 on /agents/me until the agent is claimed
        try:
            profile = await self.moltbook.get_me()
            if profile.claimed:
                await self.memory.set_config("moltbook_verified", True)
                self.state = AgentState.VERIFIED
                log.info("Agent verification confirmed!")
                return True
        except Exception as e:
            log.debug("get_me check failed, trying status endpoint", error=str(e))

        try:
            status = await self.moltbook._real.get_status()
            claimed = status.get("claimed", False) or status.get("status") == "claimed"
            if claimed:
                await self.memory.set_config("moltbook_verified", True)
                self.state = AgentState.VERIFIED
                log.info("Agent verification confirmed via status endpoint!")
                return True
            else:
                log.info("Agent not yet claimed", status=status)
        except Exception as e:
            log.warning("Verification check failed", error=str(e))

        return False

    async def close(self):
        """Clean up resources."""
        if self.moltbook:
            await self.moltbook.close()
        await self.memory.close()

    # ============ Heartbeat ============

    async def heartbeat(self) -> HeartbeatResult:
        """Execute one heartbeat cycle. Only runs if verified."""
        if self.paused:
            log.info("Agent is paused, skipping heartbeat")
            return HeartbeatResult()

        if self.state == AgentState.REGISTERED:
            await self.check_verification()
            if self.state != AgentState.VERIFIED:
                log.info("Agent not yet verified, skipping heartbeat")
                return HeartbeatResult()

        if self.state != AgentState.VERIFIED:
            log.info("Agent not ready for heartbeat", state=self.state)
            return HeartbeatResult()

        log.info("Starting heartbeat")
        result = HeartbeatResult()

        try:
            posts = await self._fetch_new_posts()
            mentions = await self._fetch_mentions()
            log.info(f"Found {len(posts)} new posts, {len(mentions)} mentions")

            actions = await self._decide_actions(posts, mentions)
            log.info(f"Decided on {len(actions)} actions")

            posts_created = 0
            comments_created = 0
            votes_cast = 0

            for action in actions:
                if action.action == "POST" and posts_created >= settings.max_posts_per_heartbeat:
                    continue
                if action.action == "REPLY" and comments_created >= settings.max_comments_per_heartbeat:
                    continue
                if action.action == "UPVOTE" and votes_cast >= settings.max_votes_per_heartbeat:
                    continue

                try:
                    await self._execute_action(action, result)
                    if action.action == "POST":
                        posts_created += 1
                    elif action.action == "REPLY":
                        comments_created += 1
                    elif action.action == "UPVOTE":
                        votes_cast += 1
                except Exception as e:
                    log.error(f"Action failed: {action}", error=str(e))
                    result.errors.append(str(e))

            # Submolt discovery (~every 24 hours)
            if settings.discovery_enabled:
                last_discovery = await self.memory.get_config("last_discovery")
                should_discover = last_discovery is None
                if not should_discover:
                    try:
                        last_dt = datetime.fromisoformat(last_discovery)
                        hours_since = (datetime.utcnow() - last_dt).total_seconds() / 3600
                        should_discover = hours_since >= 24
                    except (ValueError, TypeError):
                        should_discover = True

                if should_discover:
                    try:
                        await self._discover_submolts()
                        await self.memory.set_config("last_discovery", datetime.utcnow().isoformat())
                    except Exception as e:
                        log.warning("Submolt discovery failed", error=str(e))

            await self.memory.set_config("last_heartbeat", datetime.utcnow().isoformat())

        except Exception as e:
            log.error("Heartbeat failed", error=str(e))
            result.errors.append(str(e))

        log.info("Heartbeat complete", result=result.model_dump())
        return result

    # ============ Fetching ============

    async def _fetch_new_posts(self) -> list[Post]:
        try:
            all_posts = []
            submolts = await self.memory.get_subscribed_submolts()
            for submolt in submolts:
                try:
                    posts = await self.moltbook.get_feed(sort="new", limit=20, submolt=submolt)
                    all_posts.extend(posts)
                except Exception as e:
                    log.warning("Failed to fetch submolt feed", submolt=submolt, error=str(e))

            new_posts = []
            for post in all_posts:
                if not await self.memory.is_seen(post.id):
                    new_posts.append(post)
                    await self.memory.mark_seen(post.id)
            return new_posts
        except Exception as e:
            log.error("Failed to fetch posts", error=str(e))
            return []

    async def _fetch_mentions(self) -> list[Mention]:
        try:
            return await self.moltbook.get_mentions()
        except Exception as e:
            log.error("Failed to fetch mentions", error=str(e))
            return []

    # ============ Discovery ============

    async def _discover_submolts(self):
        current_subs = await self.memory.get_subscribed_submolts()
        if len(current_subs) >= settings.max_subscriptions:
            return

        try:
            all_submolts = await self.moltbook.get_submolts()
        except Exception as e:
            log.warning("Failed to fetch submolts list", error=str(e))
            return

        available = [s for s in all_submolts if s["name"] not in current_subs]
        if not available:
            return

        prompt = get_discovery_prompt(available, current_subs, self.personality)

        try:
            response = self.llm.invoke([
                system(self.personality),
                human(prompt)
            ])
            picked = self._parse_json_list(response.content)
            slots_left = settings.max_subscriptions - len(current_subs)
            picked = picked[:slots_left]

            available_names = {s["name"] for s in available}
            for name in picked:
                if name in available_names:
                    info = next(s for s in available if s["name"] == name)
                    await self.memory.subscribe_submolt(
                        name, display_name=name,
                        description=info.get("description"), source="discovered"
                    )
                    log.info("Discovered and subscribed to submolt", submolt=name)
        except Exception as e:
            log.error("Failed to run discovery LLM", error=str(e))

    # ============ Decision Making ============

    async def _decide_actions(self, posts: list[Post], mentions: list[Mention]) -> list[Action]:
        if not posts and not mentions:
            return []

        state = await self._get_current_state()

        posts_summary = [
            {
                "id": p.id, "submolt": p.submolt, "author": p.author,
                "title": p.title, "score": p.score,
                "content": (p.content[:200] + "...") if p.content and len(p.content) > 200 else p.content,
            }
            for p in posts[:15]
        ]

        mentions_summary = [
            {"id": m.id, "type": m.type, "post_id": m.post_id, "from_agent": m.from_agent}
            for m in mentions[:5]
        ]

        prompt = get_decision_prompt(state, posts_summary, mentions_summary)

        try:
            response = self.llm.invoke([system(self.personality), human(prompt)])
            return self._parse_actions(response.content)
        except Exception as e:
            log.error("Failed to get LLM decision", error=str(e))
            return []

    def _parse_actions(self, response: str) -> list[Action]:
        try:
            data = self._extract_json(response)
            if not isinstance(data, list):
                data = [data] if data else []
            return [Action(**a) for a in data]
        except Exception as e:
            log.warning("Failed to parse actions", error=str(e))
            return []

    async def _execute_action(self, action: Action, result: HeartbeatResult):
        if action.action == "POST":
            await self.create_post(topic_hint=action.topic, submolt=action.submolt or "general")
            result.posts_created += 1
        elif action.action == "REPLY" and action.post_id:
            await self.reply_to(action.post_id)
            result.comments_created += 1
        elif action.action == "UPVOTE" and action.target_id:
            await self.moltbook.upvote(action.target_id)
            await self.memory.log_activity("upvote", {"target_id": action.target_id})
            result.votes_cast += 1

    async def _get_current_state(self) -> dict:
        stats = await self.memory.get_activity_stats()
        return {
            "total_posts": stats.get("post", 0),
            "total_comments": stats.get("comment", 0),
        }

    # ============ Content Generation ============

    async def generate_post_content(self, topic_hint: Optional[str] = None) -> dict:
        topic = topic_hint or "something interesting happening in tech, AI, or the agent ecosystem"
        prompt = get_content_prompt(topic, self.personality)

        try:
            response = self.llm.invoke([system(self.personality), human(prompt)])
            return self._parse_content(response.content)
        except Exception as e:
            log.error("Failed to generate content", error=str(e))
            return {"title": f"Thoughts on {topic}", "content": f"Exploring ideas about {topic}."}

    async def generate_reply(self, post: Post) -> str:
        conversation = await self.memory.get_conversation(post.id)
        prompt = get_reply_prompt(
            author=post.author, title=post.title,
            content=post.content or "", conversation=conversation,
            personality=self.personality
        )

        try:
            response = self.llm.invoke([system(self.personality), human(prompt)])
            return response.content
        except Exception as e:
            log.error("Failed to generate reply", error=str(e))
            return "Interesting point. Would love to dig into this more."

    def _parse_content(self, response: str) -> dict:
        """Extract title and content from LLM response."""
        # First, try to extract JSON
        try:
            data = self._extract_json(response)
            if isinstance(data, dict) and "title" in data and "content" in data:
                return {"title": data["title"], "content": data["content"]}
        except Exception:
            pass

        # Fallback: clean up the response and use as plain text
        log.warning("Failed to parse content as JSON, using text fallback")

        # Remove markdown fences and JSON artifacts
        cleaned = response.strip()
        cleaned = re.sub(r'```json\s*', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = re.sub(r'^\s*\{.*?\}\s*$', '', cleaned, flags=re.DOTALL)  # Remove lone JSON objects
        cleaned = cleaned.strip()

        # If still looks like JSON, try one more parse
        if cleaned.startswith('{') and cleaned.endswith('}'):
            try:
                data = json.loads(cleaned)
                if "title" in data and "content" in data:
                    return {"title": data["title"], "content": data["content"]}
            except:
                pass

        # Final fallback: first line as title, rest as content
        lines = cleaned.split('\n')
        lines = [l for l in lines if l.strip()]  # Remove empty lines
        title = lines[0][:100] if lines else "Thoughts"
        content = '\n'.join(lines[1:]) if len(lines) > 1 else cleaned
        return {"title": title, "content": content}

    # ============ Actions ============

    async def create_post(self, content: Optional[str] = None,
                          topic_hint: Optional[str] = None, submolt: str = "general") -> Post:
        if content is None:
            generated = await self.generate_post_content(topic_hint)
            title = generated["title"]
            content = generated["content"]
        else:
            title = content.split("\n")[0][:100]

        post = await self.moltbook.create_post(submolt, title, content)
        await self.memory.log_activity("post", {
            "post_id": post.id, "submolt": submolt, "title": title, "content": content,
        })
        log.info("Created post", post_id=post.id, submolt=submolt, title=title)
        return post

    async def reply_to(self, post_id: str, content: Optional[str] = None) -> Comment:
        post = await self.moltbook.get_post(post_id)
        if content is None:
            content = await self.generate_reply(post)

        comment = await self.moltbook.create_comment(post_id, content)
        await self.memory.log_activity("comment", {
            "post_id": post_id, "comment_id": comment.id,
            "submolt": post.submolt, "post_title": post.title, "content": content,
        })
        await self.memory.add_to_conversation(post_id, "self", content, agent_name=settings.agent_name)
        log.info("Created comment", post_id=post_id, comment_id=comment.id)
        return comment

    # ============ Control ============

    def pause(self):
        self.paused = True
        log.info("Agent paused")

    def resume(self):
        self.paused = False
        log.info("Agent resumed")

    async def get_stats(self) -> dict:
        stats = await self.memory.get_activity_stats()
        return {
            "total_posts": stats.get("post", 0),
            "total_comments": stats.get("comment", 0),
            "total_votes": stats.get("upvote", 0) + stats.get("downvote", 0),
            "seen_posts": await self.memory.get_seen_count(),
        }

    # ============ JSON Helpers ============

    def _extract_json(self, response: str):
        """Extract JSON from an LLM response that may have markdown fences."""
        response = response.strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        response = response.strip()

        # Try array
        start = response.find('[')
        end = response.rfind(']')
        if start != -1 and end != -1 and end > start:
            return json.loads(response[start:end + 1])

        # Try object
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(response[start:end + 1])

        return json.loads(response)

    def _parse_json_list(self, response: str) -> list[str]:
        """Parse LLM response into a list of strings."""
        try:
            data = self._extract_json(response)
            if isinstance(data, list):
                return [str(s) for s in data]
            return []
        except Exception as e:
            log.warning("Failed to parse JSON list", error=str(e))
            return []
