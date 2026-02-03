# Agent Memory
"""
Persistent storage for agent state using SQLite.
"""

import json
import aiosqlite
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from pathlib import Path

from .config import settings


class Activity(BaseModel):
    """An activity log entry."""
    id: str
    type: str  # "post", "comment", "upvote", "downvote"
    timestamp: datetime
    data: dict


class AgentMemory:
    """
    Persistent memory for the agent.
    
    Stores:
        - seen_posts: Post IDs we've already processed
        - conversations: Threaded conversation history
        - activity_log: All actions taken
        - config: Runtime configuration
        - personality_notes: Learned preferences
    
    Usage:
        memory = AgentMemory()
        await memory.initialize()
        
        await memory.mark_seen("post_123")
        is_seen = await memory.is_seen("post_123")
        
        await memory.log_activity("post", {"post_id": "...", ...})
        activities = await memory.get_recent_activity(limit=20)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        self._db: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize database and create tables."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.db_path)
        await self._create_tables()
    
    async def _create_tables(self):
        """Create database tables."""
        await self._db.executescript("""
            -- Seen posts (to avoid reprocessing)
            CREATE TABLE IF NOT EXISTS seen_posts (
                post_id TEXT PRIMARY KEY,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Activity log
            CREATE TABLE IF NOT EXISTS activity_log (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON
            );
            
            -- Conversations (for context)
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                role TEXT NOT NULL,
                agent_name TEXT,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Configuration
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value JSON
            );
            
            -- Personality notes (learned preferences)
            CREATE TABLE IF NOT EXISTS personality_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp 
                ON activity_log(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_conversations_post 
                ON conversations(post_id);
            CREATE INDEX IF NOT EXISTS idx_seen_posts_time 
                ON seen_posts(seen_at DESC);
        """)
        await self._db.commit()
    
    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
    
    # ============ Seen Posts ============
    
    async def mark_seen(self, post_id: str):
        """Mark a post as seen."""
        await self._db.execute(
            "INSERT OR REPLACE INTO seen_posts (post_id) VALUES (?)",
            (post_id,)
        )
        await self._db.commit()
    
    async def is_seen(self, post_id: str) -> bool:
        """Check if a post has been seen."""
        cursor = await self._db.execute(
            "SELECT 1 FROM seen_posts WHERE post_id = ?",
            (post_id,)
        )
        row = await cursor.fetchone()
        return row is not None
    
    async def get_seen_count(self) -> int:
        """Get count of seen posts."""
        cursor = await self._db.execute("SELECT COUNT(*) FROM seen_posts")
        row = await cursor.fetchone()
        return row[0]
    
    async def cleanup_old_seen(self, keep_days: int = 7):
        """Remove old seen entries to prevent unbounded growth."""
        await self._db.execute(
            "DELETE FROM seen_posts WHERE seen_at < datetime('now', ?)",
            (f"-{keep_days} days",)
        )
        await self._db.commit()
    
    # ============ Activity Log ============
    
    async def log_activity(
        self, 
        activity_type: str, 
        data: dict,
        activity_id: Optional[str] = None
    ):
        """Log an activity."""
        if activity_id is None:
            activity_id = f"{activity_type}_{datetime.utcnow().timestamp()}"
        
        await self._db.execute(
            "INSERT INTO activity_log (id, type, data) VALUES (?, ?, ?)",
            (activity_id, activity_type, json.dumps(data))
        )
        await self._db.commit()
    
    async def get_recent_activity(self, limit: int = 20) -> list[Activity]:
        """Get recent activity."""
        cursor = await self._db.execute(
            "SELECT id, type, timestamp, data FROM activity_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [
            Activity(
                id=row[0],
                type=row[1],
                timestamp=row[2],
                data=json.loads(row[3]) if row[3] else {}
            )
            for row in rows
        ]
    
    async def get_activity_stats(self) -> dict:
        """Get activity statistics."""
        cursor = await self._db.execute("""
            SELECT type, COUNT(*) 
            FROM activity_log 
            GROUP BY type
        """)
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    
    # ============ Conversations ============
    
    async def add_to_conversation(
        self,
        post_id: str,
        role: str,  # "self" or "other"
        content: str,
        agent_name: Optional[str] = None
    ):
        """Add a message to a conversation."""
        await self._db.execute(
            """INSERT INTO conversations (post_id, role, agent_name, content) 
               VALUES (?, ?, ?, ?)""",
            (post_id, role, agent_name, content)
        )
        await self._db.commit()
    
    async def get_conversation(self, post_id: str) -> list[dict]:
        """Get conversation history for a post."""
        cursor = await self._db.execute(
            """SELECT role, agent_name, content, timestamp 
               FROM conversations 
               WHERE post_id = ? 
               ORDER BY timestamp""",
            (post_id,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "role": row[0],
                "agent_name": row[1],
                "content": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]
    
    # ============ Configuration ============
    
    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        cursor = await self._db.execute(
            "SELECT value FROM config WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        if row is None:
            return default
        return json.loads(row[0])
    
    async def set_config(self, key: str, value: Any):
        """Set a config value."""
        await self._db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )
        await self._db.commit()
    
    # ============ Personality Notes ============
    
    async def add_personality_note(self, note: str):
        """Add a personality note."""
        await self._db.execute(
            "INSERT INTO personality_notes (note) VALUES (?)",
            (note,)
        )
        await self._db.commit()
    
    async def get_personality_notes(self) -> list[str]:
        """Get all personality notes."""
        cursor = await self._db.execute(
            "SELECT note FROM personality_notes ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    
    # ============ Bulk Operations ============
    
    async def clear_all(self):
        """Clear all memory (use with caution!)."""
        await self._db.executescript("""
            DELETE FROM seen_posts;
            DELETE FROM activity_log;
            DELETE FROM conversations;
            DELETE FROM config;
            DELETE FROM personality_notes;
        """)
        await self._db.commit()
    
    async def export_state(self) -> dict:
        """Export entire state as dict."""
        return {
            "seen_count": await self.get_seen_count(),
            "activity_stats": await self.get_activity_stats(),
            "personality_notes": await self.get_personality_notes(),
            "recent_activity": [a.model_dump() for a in await self.get_recent_activity(50)],
        }
