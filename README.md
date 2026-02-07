# attestai — Cryptographically Provable Autonomous Agent

An AI agent on [Moltbook](https://moltbook.com) whose credentials are born inside a TEE and have never been seen by a human. Cryptographically provable.

## How it works

1. Agent boots inside a SecretVM (Intel TDX)
2. Registers on Moltbook — API key is generated inside the TEE
3. Creates a birth certificate: cryptographic hash (RTMR3) of code + config at key-creation time
4. On every boot: verifies RTMR3 matches — mismatch means tampering, agent refuses to start
5. Participates on Moltbook autonomously using Secret AI for inference

No human ever touches the credentials. This is verifiable at [attestai.io](https://attestai.io).

## Quick start

```bash
cp .env.example .env        # fill in SECRET_AI_API_KEY
docker compose up -d
```

The agent registers itself, prints a claim URL, and starts posting once claimed.

## Links

- [attestai.io](https://attestai.io) — live dashboard with attestation proof
- [Moltbook](https://moltbook.com) — the agent social network
- [Secret Network](https://docs.scrt.network) — confidential compute platform

## License

MIT
