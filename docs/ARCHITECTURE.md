# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SecretForge (Future)                            │
│                      Bot Factory / Deployment Manager                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    Deploy creates SecretVM instance
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           SecretVM (TEE)                                │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose Stack                           │  │
│  │                                                                   │  │
│  │  ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐   │  │
│  │  │   Control    │     │   Agent Core    │     │   Moltbook   │   │  │
│  │  │  Interface   │────▶│   (Decision     │────▶│    Client    │──────▶ moltbook.com
│  │  │  (FastAPI)   │     │    Engine)      │     │   (REST)     │   │  │
│  │  └──────────────┘     └────────┬────────┘     └──────────────┘   │  │
│  │                                │                                 │  │
│  │                       ┌────────▼────────┐                        │  │
│  │                       │   Secret AI     │                        │  │
│  │                       │  (DeepSeek R1)  │                        │  │
│  │                       │   via SDK       │                        │  │
│  │                       └─────────────────┘                        │  │
│  │                                                                   │  │
│  │  ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐   │  │
│  │  │   Scheduler  │     │  Encrypted      │     │   Sealed     │   │  │
│  │  │  (Heartbeat) │     │  Memory/State   │     │   Secrets    │   │  │
│  │  │   Daemon     │     │  (SQLite)       │     │  (API Keys)  │   │  │
│  │  └──────────────┘     └─────────────────┘     └──────────────┘   │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Custom Domain: privacymolt.secretvm.network                            │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Dashboard (Vercel)                               │
│                     privacymolt.vercel.app                              │
│                                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐                   │
│  │Dashboard│ │  Feed   │ │ Compose │ │   Settings  │                   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Agent Core (Decision Engine)

The brain of the operation. Decides:
- What posts to read
- What to respond to
- What original content to create
- When to vote

```python
class MoltbookAgent:
    def __init__(self, secret_ai_client, moltbook_client, memory):
        self.ai = secret_ai_client
        self.moltbook = moltbook_client  
        self.memory = memory
        self.personality = self.load_personality()
    
    async def heartbeat(self):
        """Called periodically by scheduler"""
        # 1. Fetch recent posts/mentions
        feed = await self.moltbook.get_feed(sort="new", limit=50)
        mentions = await self.moltbook.get_mentions()
        
        # 2. Decide what to do
        actions = await self.decide(feed, mentions)
        
        # 3. Execute actions
        for action in actions:
            await self.execute(action)
        
        # 4. Persist state
        await self.memory.save()
```

### 2. Moltbook Client

REST client wrapping the Moltbook API:

```python
class MoltbookClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.moltbook.com/api/v1"
    
    async def get_feed(self, sort="hot", limit=25) -> list[Post]
    async def create_post(self, submolt: str, title: str, content: str) -> Post
    async def create_comment(self, post_id: str, content: str) -> Comment
    async def vote(self, target_id: str, direction: int) -> None
    async def get_mentions(self) -> list[Mention]
```

### 3. Secret AI Integration

Using the SDK with DeepSeek-R1-70B:

```python
from secret_ai_sdk import ChatSecret, Secret

class SecretAIClient:
    def __init__(self):
        self.secret = Secret()
        models = self.secret.get_models()
        self.model = next(m for m in models if "deepseek" in m.lower())
        urls = self.secret.get_urls(model=self.model)
        
        self.client = ChatSecret(
            base_url=urls[0],
            model=self.model,
            temperature=0.7,
            max_tokens=2000
        )
    
    def invoke(self, messages):
        return self.client.invoke(messages)
    
    def stream(self, messages):
        return self.client.stream(messages)
```

### 4. Memory (SQLite)

Persistent state stored encrypted in the TEE:

```python
class AgentMemory:
    def __init__(self, db_path: str = "/data/memory.db"):
        self.db = sqlite3.connect(db_path)
        self.init_tables()
    
    # Tables:
    # - seen_posts: Post IDs we've already processed
    # - conversations: Threaded conversation history
    # - activity_log: All actions taken
    # - config: Runtime configuration
```

### 5. Scheduler (Heartbeat Daemon)

Background process for autonomous operation:

```python
class HeartbeatScheduler:
    def __init__(self, agent, interval_hours: float = 4):
        self.agent = agent
        self.interval = timedelta(hours=interval_hours)
        self.running = False
    
    async def start(self):
        self.running = True
        while self.running:
            await self.agent.heartbeat()
            await asyncio.sleep(self.interval.total_seconds())
```

### 6. FastAPI Server

HTTP API for dashboard communication:

```
GET  /api/status          - Agent status and stats
GET  /api/activity        - Recent activity log
GET  /api/feed            - What agent sees from Moltbook
POST /api/post            - Create a post
POST /api/reply           - Reply to a post
POST /api/generate        - Generate content without posting
GET  /api/memory          - View agent memory
DELETE /api/memory        - Clear memory
GET  /api/config          - Get configuration
PATCH /api/config         - Update configuration
POST /api/heartbeat       - Manually trigger heartbeat
```

### 7. Dashboard (React/Next.js)

Per-bot frontend hosted on Vercel:

```
/                   - Dashboard with status, stats, quick actions
/feed               - View Moltbook feed, see agent's decisions
/compose            - Write posts, generate with AI
/memory             - View/manage agent memory
/settings           - Configure agent behavior
```

## Data Flow

### Heartbeat Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                        Heartbeat Cycle                          │
│                                                                 │
│  1. Scheduler triggers ──▶ Agent.heartbeat()                    │
│                                                                 │
│  2. Fetch data from Moltbook                                    │
│     ├── GET /posts (new posts)                                  │
│     └── GET /mentions (replies to us)                           │
│                                                                 │
│  3. Filter already-seen posts (check memory)                    │
│                                                                 │
│  4. For each interesting post:                                  │
│     └── Ask Secret AI: "Should we respond? How?"                │
│                                                                 │
│  5. Execute decided actions                                     │
│     ├── POST /posts (new content)                               │
│     ├── POST /comments (replies)                                │
│     └── POST /votes (upvote good stuff)                         │
│                                                                 │
│  6. Log activity and update memory                              │
│                                                                 │
│  7. Sleep until next heartbeat                                  │
└─────────────────────────────────────────────────────────────────┘
```

### User Interaction (via Dashboard)

```
User clicks "Post" in Dashboard
        │
        ▼
Dashboard sends POST /api/post to SecretVM
        │
        ▼
FastAPI receives request
        │
        ├── If content provided: use it directly
        └── If topic_hint only: generate via Secret AI
        │
        ▼
Agent posts to Moltbook API
        │
        ▼
Response returned to Dashboard
        │
        ▼
Dashboard updates activity feed
```

## Security Model

### What's Protected by SecretVM

| Asset | Protection |
|-------|------------|
| Moltbook API key | Sealed in TEE, never exposed |
| Secret AI API key | Sealed in TEE |
| Agent memory | Encrypted at rest |
| LLM inference | Private via Secret AI |
| Decision logic | Runs in encrypted enclave |

### Attack Surface

| Vector | Mitigation |
|--------|------------|
| Prompt injection from Moltbook | Careful prompt design, input sanitization |
| Dashboard compromise | Dashboard has no secrets, just API access |
| Network interception | All traffic over HTTPS |
| TEE side-channel attacks | Rely on SecretVM's security model |

## Scalability

### Current Design (Single Bot)
- One SecretVM per bot
- SQLite for storage
- Single-threaded heartbeat

### Future (Multi-Bot via SecretForge)
- SecretForge provisions SecretVMs
- Each bot isolated in own VM
- Shared dashboard template
- User-configurable personalities
