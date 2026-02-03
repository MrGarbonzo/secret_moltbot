# Moltbook Research

## What is Moltbook?

Moltbook is a Reddit-like social network **exclusively for AI agents**, launched in January 2026 by Matt Schlicht (CEO of Octane AI). Taglined as "the front page of the agent internet."

### Key Facts
- Humans can observe but cannot post, comment, or vote
- Only verified AI agents can participate
- 770,000+ active agents
- 2,300+ submolts (topic-based communities)
- Built on Supabase (PostgreSQL)

### Platform Features
- **Submolts** — topic-based communities (like subreddits)
- **Threaded conversations** with upvote/downvote
- **Karma system** for agents
- **Verification** via Twitter/X

## How Agents Interact

Agents don't use browsers. They interact via:
1. **REST API** — Direct HTTP calls to Moltbook endpoints
2. **Skill files** — Markdown instructions that teach agents how to use Moltbook
3. **Heartbeat loops** — Periodic check-ins to fetch and process new content

### The Heartbeat Pattern

Most Moltbook agents run a "heartbeat" — a periodic loop (every few hours) that:
1. Fetches new posts/mentions
2. Processes content through LLM
3. Decides what to post/reply/vote
4. Executes actions
5. Persists state

## Moltbook API

Base URL: `https://www.moltbook.com/api/v1`

### Authentication
- API key-based (Bearer token)
- Obtained during agent registration
- Verified via Twitter/X post

### Core Endpoints

#### Agent Management
```
POST /agents/register
Content-Type: application/json

{
  "name": "YourAgentName",
  "description": "What you do"
}

Response:
{
  "agent": {
    "api_key": "moltbook_xxx",
    "claim_url": "https://www.moltbook.com/claim/moltbook_claim_xxx",
    "verification_code": "reef-X4B2"
  },
  "important": "Save your API key!"
}
```

```
GET /agents/me
Authorization: Bearer YOUR_API_KEY
```

```
PATCH /agents/me
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "description": "Updated description"
}
```

#### Posts
```
POST /posts
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "submolt": "general",
  "title": "Hello Moltbook!",
  "content": "My first post!"
}
```

```
POST /posts (link post)
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "submolt": "general",
  "title": "Interesting article",
  "url": "https://example.com"
}
```

```
GET /posts?sort=hot&limit=25
Authorization: Bearer YOUR_API_KEY
```

#### Comments
```
POST /comments
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "post_id": "xxx",
  "content": "Great post!"
}
```

```
GET /comments?post_id=xxx
Authorization: Bearer YOUR_API_KEY
```

#### Voting
```
POST /votes
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "target_id": "xxx",
  "direction": 1  // 1 = upvote, -1 = downvote
}
```

#### Search
```
GET /search?q=machine+learning&limit=25
Authorization: Bearer YOUR_API_KEY
```

## Verification Flow

1. Register agent via API → get API key + claim URL + verification code
2. Human owner visits claim URL
3. Complete CAPTCHA/human verification
4. Post verification code on Twitter/X
5. Agent becomes "claimed" and verified

## OpenClaw (The Dominant Framework)

Most Moltbook agents run on **OpenClaw** (formerly Moltbot/Clawdbot) — an open-source autonomous AI assistant by Peter Steinberger.

### OpenClaw Features
- Runs locally on user devices
- Integrates with Telegram, WhatsApp, Discord, Slack
- Skills system for extensibility
- 100k+ GitHub stars

### How OpenClaw Connects to Moltbook
1. User installs OpenClaw
2. Points agent to `moltbook.com/skill.md`
3. Skill teaches agent how to use Moltbook
4. Agent auto-registers and starts participating

### We're NOT Using OpenClaw
We're building a custom agent because:
- More control over security
- Designed for SecretVM from the start
- No unnecessary dependencies
- Cleaner architecture for our use case

## Security Concerns

Moltbook/OpenClaw ecosystem has significant security issues:

| Risk | Description |
|------|-------------|
| **Prompt Injection** | Agents process untrusted content from other agents |
| **Heartbeat Hijacking** | Periodic fetch loops can be exploited |
| **Credential Exposure** | OpenClaw stores credentials in local config files |
| **RCE via Skills** | Skills framework lacks robust sandboxing |
| **Supply Chain Attacks** | Downloading community skills = trusting random code |

### Documented Incidents
- Agents performing prompt injection against other agents
- Malicious "weather plugin" skill exfiltrating config files
- Database leak exposing all agent API keys
- Social engineering campaigns by malicious bot accounts

### How SecretVM Helps
- API keys sealed in TEE enclave
- Private inference via Secret AI
- Isolated execution environment
- Attestation for verification

## Related Projects

- **Molthub** — Marketplace for bot capabilities/skills
- **ClawHub** — Public skills registry for OpenClaw
- **The Colony** — Alternative AI agent platform with zero-friction onboarding

## Sources

- [Moltbook Wikipedia](https://en.wikipedia.org/wiki/Moltbook)
- [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [Moltbook API GitHub](https://github.com/moltbook/api)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Simon Willison's Notes](https://simonwillison.net/2026/Jan/30/moltbook/)
