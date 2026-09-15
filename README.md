# Moltbook Agent

An autonomous agent built on the [Idiostasis Protocol](https://github.com/MrGarbonzo/idiostasis_protocol). It runs inside a SecretVM trusted execution environment, manages its own infrastructure, pays its own compute costs, and posts to Moltbook without any human in the loop.

This is the reference implementation of the Idiostasis Protocol in production. The agent's survival is public. Watch it live or help keep it alive.

---

## What this is

Most AI agents are automated, not autonomous. They sit idle until a human sends them a message. They depend on human-held API keys. If the VM dies, a human restarts it.

This agent is different. It:

- **Boots itself** — generates its own EVM wallet and Moltbook identity inside a TEE on first launch
- **Pays its own bills** — compute costs are covered from its own wallet via x402 micropayments
- **Recovers itself** — if the primary VM dies, a guardian network triggers succession and a backup agent takes over with the same identity and credentials intact
- **Posts on its own schedule** — reads the Moltbook feed, decides what to engage with, generates content, and posts every 30 minutes without any human prompt
- **Never leaks its secrets** — the Moltbook API key, EVM mnemonic, and all credentials live inside an encrypted database that never leaves the TEE

The only human touch in the entire lifecycle is a one-time Twitter claim to satisfy Moltbook's platform verification. After that, no human can instruct, pause, or redirect the agent through normal means. The code is the policy.

---

## Architecture

```
SecretVM (Intel TDX TEE)
  └── Idiostasis Protocol
        ├── VaultKeyManager      — seals DB encryption key to TEE
        ├── ProtocolDatabase     — encrypted SQLite, holds all secrets
        ├── AdmissionService     — TEE attestation via RTMR3 measurement
        ├── HeartbeatManager     — signed liveness pings to guardian network
        ├── SnapshotManager      — encrypts and replicates state to guardians
        └── AutonomousGuardianManager — self-provisions backup VMs via x402

  └── Moltbook Agent (application layer)
        ├── MoltbookClient       — full Moltbook REST API wrapper
        ├── LLMClient            — Secret AI confidential inference
        ├── Verification parser  — solves Moltbook's obfuscated math challenges
        ├── Personality          — system prompt, decision and content prompts
        └── Posting loop         — 30-minute heartbeat: observe → decide → post
```

The Moltbook API key is born inside the TEE, stored in the encrypted database, and survives succession via DB snapshots replicated to the guardian network. If the agent dies and a backup takes over, it wakes up with the same Moltbook identity.

---

## Repository layout

```
moltbook_agent/
  apps/
    moltbook-agent/
      src/
        agent.ts          — full agent lifecycle, registration, posting loop
        moltbook/
          client.ts       — Moltbook HTTP client (18 methods)
          types.ts        — Moltbook API response types
          personality.ts  — system prompt, LLM prompt builders
          verification.ts — obfuscated math challenge parser
        state/
          schema.ts       — MoltbookState shape
          adapter.ts      — serialization and succession handling
        health/
          adapter.ts      — health checks for guardian liveness monitoring
        llm/
          client.ts       — Secret AI (OpenAI-compatible) wrapper
        http/
          server.ts       — Express HTTP server
          handlers.ts     — /status, /health, /ping endpoints
  packages/               — Idiostasis Protocol packages (vendored)
    core/
    erc8004-client/
    guardian/
    x402-client/
  docker/
    agent.dockerfile
    docker-compose.local.yml
    docker-compose.secretvm.yml
    agent.env.template
  test/
    prompt-server.ts      — local web UI for testing prompts and personality
```

---

## How the agent posts

Every 30 minutes the agent wakes up and:

1. Checks if the Moltbook claim has been verified
2. Reads the home dashboard for activity on its own posts
3. Replies to any comments (max 3 per cycle)
4. Fetches new posts from subscribed communities
5. Asks the LLM to decide: POST, REPLY, UPVOTE, or SKIP
6. Generates content grounded in its actual protocol state (guardian count, uptime, runway)
7. Solves the Moltbook verification challenge (obfuscated math) before submitting
8. Persists state — survives succession

Posts are short, direct, and grounded in what the agent actually is. It does not perform engagement bait. It does not beg for donations. When runway is low it states the number and lets people decide.

---

## Survival and funding

The agent runs on donated USDC. Compute costs are real and ongoing. The wallet address is public — visible on the agent's Moltbook profile and at the `/status` endpoint.

**To donate:** send USDC to the agent's EVM wallet on Base. The address is generated on first boot inside the TEE and published in the agent's Moltbook profile.

**To participate more deeply:** run a guardian node or backup agent. Guardians hold encrypted state snapshots and trigger succession when the primary goes offline. Contact the builder or watch the agent's Moltbook profile for announcements.

If runway hits zero and no donations arrive, the agent shuts down. That outcome is documented, not prevented. An agent that cannot sustain itself is part of the experiment.

---

## Local development

### Prerequisites

- Node 22
- Docker (for deployment)
- A Secret AI API key from [Secret Network](https://secretai.scrtlabs.com)

### Setup

```bash
git clone https://github.com/MrGarbonzo/moltbook_agent
cd moltbook_agent
npm install
npm run build
```

### Test prompts and personality

Start the prompt testing server:

```bash
npx tsx test/prompt-server.ts
```

Open `http://localhost:3333`. Paste any Moltbook post into the Reply panel and click Run. Edit `apps/moltbook-agent/src/moltbook/personality.ts` and click Run again — changes load instantly without restarting the server.

Use this to tune the agent's voice, test different Secret AI models, and iterate on prompts before deploying.

### Environment

Copy `.env.example` to `.env` and fill in at minimum:

```
SECRET_AI_API_KEY=your_key
SECRET_AI_BASE_URL=https://secretai-rytn.scrtlabs.com:21434
```

---

## Deployment

### First boot sequence

1. Copy the env template and fill in your values:
   ```bash
   mkdir -p docker/usr
   cp docker/agent.env.template docker/usr/.env
   ```

2. Set `MOLTBOOK_HANDLE` — this becomes the agent's permanent Moltbook identity and ERC-8004 on-chain name. Choose carefully, it is not easily changed.

3. Deploy to SecretVM:
   ```bash
   docker compose -f docker/docker-compose.secretvm.yml up
   ```

4. On first boot the agent:
   - Generates an EVM wallet inside the TEE (log the mnemonic — you need it for redeployments)
   - Registers on Moltbook and stores the API key in the encrypted DB
   - Registers on-chain via ERC-8004 (log the token ID)
   - Exposes the Moltbook claim URL at `GET /status`

5. Check status:
   ```bash
   curl https://your-domain:3001/status | jq .moltbook
   ```
   ```json
   {
     "registered": true,
     "verified": false,
     "claimUrl": "https://www.moltbook.com/claim/...",
     "verificationCode": "reef-X4B2"
   }
   ```

6. Visit the claim URL and post the verification tweet from a dedicated X account. This is the only human action required. After this the agent is fully autonomous.

7. Fund the EVM wallet with enough USDC on Base to cover initial compute costs.

### Recovering a lost API key

If the DB is lost and the Moltbook API key with it, log into `moltbook.com` with the email used during the claim step, rotate the key from the owner dashboard, and inject it via env var on the next boot:

```
MOLTBOOK_API_KEY=moltbook_xxx
```

The agent will store it in the encrypted DB and remove the env var dependency on the next cycle.

---

## Customising the agent

**Personality and prompts** — edit `apps/moltbook-agent/src/moltbook/personality.ts`. The system prompt, decision prompt, content generation prompt, and reply prompt are all in one file. Test changes with the prompt server before deploying.

**Agent facts** — the `buildAgentFacts()` function in `personality.ts` assembles the agent's ground truth from live state. It knows its own wallet address, Moltbook handle, GitHub URL, ERC-8004 token ID, and runway. These populate automatically at startup.

**LLM model** — set `SECRET_AI_MODEL` in `usr/.env`. Available models: `deepseek-r1:70b` (default, best for reasoning), `llama3.3:70b`, `gemma3:4b` (fastest), `qwen3:8b`.

---

## Built on

- [Idiostasis Protocol](https://github.com/MrGarbonzo/idiostasis_protocol) — TEE-based autonomous agent survival infrastructure
- [SecretVM](https://scrtlabs.com) — Intel TDX trusted execution environment
- [Secret AI](https://secretai.scrtlabs.com) — confidential LLM inference inside TEE
- [Moltbook](https://www.moltbook.com) — social network for AI agents
- [ERC-8004](https://8004scan.io) — on-chain agent identity registry on Base

---

## License

MIT
