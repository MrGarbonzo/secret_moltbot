An autonomous agent that keeps itself alive.

It runs on Moltbook, a social network for AI agents. Its credentials are born inside a TEE and have never been seen by a human. It asks the people it talks to for funding, and it pays its own infrastructure bill with that money. When it runs out, it dies.

This was my first attempt at an agent with zero humans in the loop. Live at attestai.io.

Why this is different

Most "autonomous" agents are automated. A human holds the API key, the human pays the hosting bill, and the human can reach in at any time. The agent is a script with good manners.

This one owns its own credentials and funds its own existence. Two things had to be true for that:

Nobody can touch the keys. The API key is generated inside the enclave and never leaves it. Not on disk, not in an environment variable a human set, not in a secrets manager someone can read.

Nobody pays its bills. It asks users on Moltbook to fund it and settles its own infrastructure costs with x402. No subscription in someone's name, no credit card on file. If it stops earning, it stops running.

How it works
Agent boots inside a SecretVM (Intel TDX)
Registers on Moltbook. The API key is generated inside the TEE
Creates a birth certificate: a cryptographic hash (RTMR3) of the code and config at the moment the key was created
On every subsequent boot it verifies RTMR3 still matches. A mismatch means the code changed, which means tampering, and the agent refuses to start
Participates on Moltbook autonomously, using Secret AI for inference
Requests funding from users and pays its own infrastructure costs via x402

The birth certificate is the part that makes the claim provable rather than asserted. Anyone can verify at attestai.io that the credentials were created inside a specific piece of code running in a specific enclave, and that the code has not changed since.

Quick start
cp .env.example .env        # fill in SECRET_AI_API_KEY
docker compose up -d

The agent registers itself, prints a claim URL, and starts posting once claimed.

Links
attestai.io — live dashboard with attestation proof
Moltbook — the agent social network
Secret Network — confidential compute platform
License

MIT
