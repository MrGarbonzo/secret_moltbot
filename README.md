# SecretMolt - Privacy-Preserving Moltbook Agent

A Moltbook AI agent running inside SecretVM with Secret AI (DeepSeek-R1-70B), demonstrating privacy-preserving autonomous agents.

## What is This?

This project creates an autonomous AI agent that participates on [Moltbook](https://moltbook.com) — a Reddit-like social network exclusively for AI agents. The unique aspect: our agent runs inside a **SecretVM** (Trusted Execution Environment) using **Secret AI** for inference, meaning:

- All agent thoughts/decisions are encrypted
- Memory is encrypted at rest
- Inference happens privately (queries don't leak to providers)
- API keys are sealed in the enclave
- The agent practices what it preaches about privacy

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SecretVM (TEE)                           │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Docker Compose Stack                       │   │
│   │                                                         │   │
│   │   ┌───────────────┐    ┌───────────────────────────┐   │   │
│   │   │   FastAPI     │    │      Agent Core           │   │   │
│   │   │   (Port 8000) │◄──►│  - Moltbook Client        │   │   │
│   │   │               │    │  - Secret AI (DeepSeek)   │   │   │
│   │   └───────────────┘    │  - Memory (SQLite)        │   │   │
│   │                        │  - Scheduler              │   │   │
│   │                        └───────────────────────────┘   │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   Custom Domain: privacymolt.secretvm.network                   │
└───────────────────────────────────────────────────────────────┬─┘
                                                                │
                    HTTPS                                       │
                                                                │
┌───────────────────────────────────────────────────────────────▼─┐
│                     Dashboard (Vercel)                          │
│                  privacymolt.vercel.app                         │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
secretmolt/
├── agent/                      # Python backend (runs in SecretVM)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI entry point
│   │   ├── agent.py            # Core agent logic
│   │   ├── moltbook.py         # Moltbook API client
│   │   ├── llm.py              # Secret AI wrapper
│   │   ├── memory.py           # SQLite persistence
│   │   ├── scheduler.py        # Heartbeat daemon
│   │   ├── personality.py      # System prompts
│   │   └── config.py           # Environment config
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── dashboard/                  # Next.js frontend (deploy to Vercel)
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── package.json
│   └── .env.example
│
├── docs/                       # Documentation
│   ├── MOLTBOOK.md            # Moltbook platform info
│   ├── ARCHITECTURE.md        # Detailed architecture
│   ├── IMPLEMENTATION.md      # Implementation plan
│   └── API.md                 # API reference
│
└── README.md
```

## Quick Start

### Prerequisites
- SecretVM access
- Secret AI API key
- Twitter/X account (for Moltbook verification)

### Deployment

1. Clone this repo into your SecretVM
2. Configure environment variables (see `.env.example`)
3. Run `docker-compose up -d`
4. Register agent on Moltbook via the API
5. Verify via Twitter
6. Agent starts participating autonomously

## Bot Personality

The first bot is **PrivacyMolt** — a privacy maximalist and evangelist that:
- Advocates for privacy as a fundamental right
- Educates about confidential computing, TEEs, encryption
- Demonstrates privacy-preserving AI by existing
- Engages thoughtfully in discussions about digital sovereignty

See `docs/PERSONALITY.md` for the full system prompt.

## Future: SecretForge Integration

Once this single bot is working, we'll integrate with SecretForge to allow anyone to deploy their own Moltbook agent with custom personalities.

## Links

- [Moltbook](https://moltbook.com)
- [Secret Network Docs](https://docs.scrt.network)
- [SecretVM Documentation](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/introduction)
- [Secret AI SDK](https://github.com/scrtlabs/secret-ai-sdk)

## License

MIT
