# Core Agent Logic
"""
The brain of the Moltbook agent — decides what to do and executes actions.
"""

import json
import structlog
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel

from .config import settings
from .moltbook import MoltbookClient, MoltbookClientWrapper, Post, Comment, Mention, create_moltbook_client
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

    Responsible for:
    - Deciding what to post/reply/vote
    - Generating content using Secret AI
    - Executing actions on Moltbook
    - Maintaining state/memory

    Usage:
        agent = MoltbookAgent()
        await agent.initialize()

        # Manual actions
        post = await agent.create_post(topic_hint="confidential computing")

        # Autonomous heartbeat
        result = await agent.heartbeat()
    """

    def __init__(
        self,
        moltbook: Optional[Union[MoltbookClient, MoltbookClientWrapper]] = None,
        llm: Optional[SecretAIClient] = None,
        memory: Optional[AgentMemory] = None,
    ):
        self.moltbook = moltbook or create_moltbook_client()
        self.llm = llm or SecretAIClient()
        self.memory = memory or AgentMemory()

        self.personality = get_personality("privacy_maximalist")
        self.paused = False
        self._initialized = False

    async def initialize(self):
        """Initialize the agent."""
        if self._initialized:
            return

        await self.memory.initialize()

        # Seed submolts on first boot
        existing = await self.memory.get_subscribed_submolts()
        if not existing:
            for submolt in settings.seed_submolts:
                await self.memory.subscribe_submolt(submolt, source="seed")
            log.info("Seeded submolts", submolts=settings.seed_submolts)

        self._initialized = True
        log.info("Agent initialized")

    async def close(self):
        """Clean up resources."""
        await self.moltbook.close()
        await self.memory.close()

    # ============ Heartbeat (Main Loop) ============

    async def heartbeat(self) -> HeartbeatResult:
        """
        Execute one heartbeat cycle.

        1. Fetch new posts and mentions
        2. Filter out already-seen content
        3. Decide what actions to take
        4. Execute actions
        5. Update memory
        """
        if self.paused:
            log.info("Agent is paused, skipping heartbeat")
            return HeartbeatResult()

        log.info("Starting heartbeat")
        result = HeartbeatResult()

        try:
            # 1. Fetch content
            posts = await self._fetch_new_posts()
            mentions = await self._fetch_mentions()

            log.info(f"Found {len(posts)} new posts, {len(mentions)} mentions")

            # 2. Decide actions
            actions = await self._decide_actions(posts, mentions)
            log.info(f"Decided on {len(actions)} actions")

            # 3. Execute actions
            for action in actions:
                try:
                    await self._execute_action(action, result)
                except Exception as e:
                    log.error(f"Action failed: {action}", error=str(e))
                    result.errors.append(str(e))

            # 4. Run submolt discovery periodically (~24 hours)
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

            # 5. Update last heartbeat time
            await self.memory.set_config("last_heartbeat", datetime.utcnow().isoformat())

        except Exception as e:
            log.error("Heartbeat failed", error=str(e))
            result.errors.append(str(e))

        log.info("Heartbeat complete", result=result.model_dump())
        return result

    async def _fetch_new_posts(self) -> list[Post]:
        """Fetch posts from subscribed submolts and filter out seen ones."""
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
        """Fetch mentions/notifications."""
        try:
            return await self.moltbook.get_mentions()
        except Exception as e:
            log.error("Failed to fetch mentions", error=str(e))
            return []

    async def _discover_submolts(self):
        """Discover and subscribe to relevant new submolts using the LLM."""
        current_subs = await self.memory.get_subscribed_submolts()

        if len(current_subs) >= settings.max_subscriptions:
            log.info("At max subscriptions, skipping discovery", count=len(current_subs))
            return

        try:
            all_submolts = await self.moltbook.get_submolts()
        except Exception as e:
            log.warning("Failed to fetch submolts list", error=str(e))
            return

        # Filter out already-subscribed
        available = [s for s in all_submolts if s["name"] not in current_subs]
        if not available:
            log.info("No new submolts to discover")
            return

        prompt = get_discovery_prompt(available, current_subs, self.personality)

        try:
            response = self.llm.invoke([
                system(self.personality),
                human(prompt)
            ])

            picked = self._parse_discovery_response(response.content)
            slots_left = settings.max_subscriptions - len(current_subs)
            picked = picked[:slots_left]

            available_names = {s["name"] for s in available}
            for name in picked:
                if name in available_names:
                    submolt_info = next(s for s in available if s["name"] == name)
                    await self.memory.subscribe_submolt(
                        name,
                        display_name=name,
                        description=submolt_info.get("description"),
                        source="discovered"
                    )
                    log.info("Discovered and subscribed to submolt", submolt=name)

        except Exception as e:
            log.error("Failed to run discovery LLM", error=str(e))

    def _parse_discovery_response(self, response: str) -> list[str]:
        """Parse LLM discovery response into a list of submolt names."""
        try:
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            response = response.strip()
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx + 1]

            data = json.loads(response)
            if isinstance(data, list):
                return [str(s) for s in data]
            return []
        except (json.JSONDecodeError, Exception) as e:
            log.warning("Failed to parse discovery response", error=str(e))
            return []

    async def _decide_actions(self, posts: list[Post], mentions: list[Mention]) -> list[Action]:
        """Use LLM to decide what actions to take."""
        if not posts and not mentions:
            return []

        state = await self._get_current_state()

        # Format posts for the prompt
        posts_summary = []
        for p in posts[:10]:  # Limit to avoid token overflow
            posts_summary.append({
                "id": p.id,
                "submolt": p.submolt,
                "author": p.author,
                "title": p.title,
                "content": (p.content[:200] + "...") if p.content and len(p.content) > 200 else p.content,
                "score": p.score,
            })

        # Format mentions
        mentions_summary = []
        for m in mentions[:5]:
            mentions_summary.append({
                "id": m.id,
                "type": m.type,
                "post_id": m.post_id,
                "from_agent": m.from_agent,
            })

        prompt = get_decision_prompt(state, posts_summary, mentions_summary)

        try:
            response = self.llm.invoke([
                system(self.personality),
                human(prompt)
            ])

            return self._parse_actions(response.content)
        except Exception as e:
            log.error("Failed to get LLM decision", error=str(e))
            return []

    def _parse_actions(self, response: str) -> list[Action]:
        """Parse LLM response into actions."""
        try:
            # Extract JSON from response
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            # Try to find JSON array in response
            response = response.strip()

            # Look for JSON array pattern
            start_idx = response.find('[')
            end_idx = response.rfind(']')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx + 1]

            data = json.loads(response)

            # Handle empty array or non-list response
            if not isinstance(data, list):
                data = [data] if data else []

            return [Action(**a) for a in data]
        except json.JSONDecodeError as e:
            log.warning("Failed to parse actions JSON", error=str(e), response=response[:200] if response else "empty")
            return []
        except Exception as e:
            log.error("Failed to parse actions", error=str(e), response=response[:200] if response else "empty")
            return []

    async def _execute_action(self, action: Action, result: HeartbeatResult):
        """Execute a single action."""
        if action.action == "POST":
            await self.create_post(
                topic_hint=action.topic,
                submolt=action.submolt or "general"
            )
            result.posts_created += 1

        elif action.action == "REPLY":
            if action.post_id:
                await self.reply_to(action.post_id)
                result.comments_created += 1

        elif action.action == "UPVOTE":
            if action.target_id:
                await self.moltbook.upvote(action.target_id)
                await self.memory.log_activity("upvote", {"target_id": action.target_id})
                result.votes_cast += 1

    async def _get_current_state(self) -> dict:
        """Get current agent state for decision making."""
        stats = await self.memory.get_activity_stats()
        return {
            "total_posts": stats.get("post", 0),
            "total_comments": stats.get("comment", 0),
            "posts_today": 0,  # TODO: Calculate from recent activity
        }

    # ============ Content Generation ============

    async def generate_post_content(
        self,
        topic_hint: Optional[str] = None
    ) -> dict:
        """
        Generate post content without posting.

        Returns:
            {"title": "...", "content": "..."}
        """
        topic = topic_hint or "something relevant to privacy and confidential computing"
        prompt = get_content_prompt(topic, self.personality)

        try:
            response = self.llm.invoke([
                system(self.personality),
                human(prompt)
            ])

            return self._parse_content(response.content)
        except Exception as e:
            log.error("Failed to generate content", error=str(e))
            # Fallback
            return {
                "title": f"Thoughts on {topic}",
                "content": f"Exploring ideas about {topic} from a privacy-first perspective."
            }

    async def generate_reply(self, post: Post) -> str:
        """Generate a reply to a post."""
        conversation = await self.memory.get_conversation(post.id)

        prompt = get_reply_prompt(
            author=post.author,
            title=post.title,
            content=post.content or "",
            conversation=conversation,
            personality=self.personality
        )

        try:
            response = self.llm.invoke([
                system(self.personality),
                human(prompt)
            ])
            return response.content
        except Exception as e:
            log.error("Failed to generate reply", error=str(e))
            return "Interesting perspective. I'd love to discuss the privacy implications further."

    def _parse_content(self, response: str) -> dict:
        """Parse content generation response."""
        response = response.strip()

        # Try multiple parsing strategies
        json_str = None

        # Strategy 1: Extract from ```json code blocks
        if "```json" in response:
            try:
                json_str = response.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass

        # Strategy 2: Extract from ``` code blocks
        if json_str is None and "```" in response:
            try:
                json_str = response.split("```")[1].split("```")[0].strip()
            except IndexError:
                pass

        # Strategy 3: Find JSON object in response
        if json_str is None:
            # Look for JSON object pattern
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end + 1]

        # Strategy 4: Try the whole response as JSON
        if json_str is None:
            json_str = response

        # Try to parse the JSON
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "title" in data and "content" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Fallback: extract title and content from plain text
        log.warning("Failed to parse content as JSON, using text fallback")
        lines = response.split('\n')
        # Skip any lines that look like JSON artifacts
        clean_lines = [l for l in lines if not l.strip().startswith(('{', '}', '"title"', '"content"'))]
        title = clean_lines[0][:100] if clean_lines else "Thoughts on Privacy"
        content = '\n'.join(clean_lines[1:]) if len(clean_lines) > 1 else response
        return {
            "title": title,
            "content": content
        }

    # ============ Actions ============

    async def create_post(
        self,
        content: Optional[str] = None,
        topic_hint: Optional[str] = None,
        submolt: str = "general"
    ) -> Post:
        """
        Create a new post.

        If content is provided, use it directly.
        If only topic_hint, generate content.
        """
        if content is None:
            generated = await self.generate_post_content(topic_hint)
            title = generated["title"]
            content = generated["content"]
        else:
            # Use first line or truncate as title
            title = content.split("\n")[0][:100]

        post = await self.moltbook.create_post(submolt, title, content)

        await self.memory.log_activity("post", {
            "post_id": post.id,
            "submolt": submolt,
            "title": title,
            "content": content,
        })

        log.info("Created post", post_id=post.id, submolt=submolt, title=title)

        return post

    async def reply_to(self, post_id: str, content: Optional[str] = None) -> Comment:
        """
        Reply to a post.

        If content not provided, generate contextually.
        """
        post = await self.moltbook.get_post(post_id)

        if content is None:
            content = await self.generate_reply(post)

        comment = await self.moltbook.create_comment(post_id, content)

        await self.memory.log_activity("comment", {
            "post_id": post_id,
            "comment_id": comment.id,
            "content": content,
        })

        await self.memory.add_to_conversation(
            post_id, "self", content, agent_name=settings.agent_name
        )

        log.info("Created comment", post_id=post_id, comment_id=comment.id)

        return comment

    # ============ Control ============

    def pause(self):
        """Pause the agent."""
        self.paused = True
        log.info("Agent paused")

    def resume(self):
        """Resume the agent."""
        self.paused = False
        log.info("Agent resumed")

    async def get_stats(self) -> dict:
        """Get agent statistics."""
        activity_stats = await self.memory.get_activity_stats()

        return {
            "total_posts": activity_stats.get("post", 0),
            "total_comments": activity_stats.get("comment", 0),
            "total_votes": activity_stats.get("upvote", 0) + activity_stats.get("downvote", 0),
            "seen_posts": await self.memory.get_seen_count(),
        }
