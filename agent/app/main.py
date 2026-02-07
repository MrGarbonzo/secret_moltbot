# FastAPI Application
"""
HTTP API for monitoring the autonomous Moltbook agent.

Endpoints are state-aware. The dashboard checks /api/status and
renders different views based on the agent's lifecycle state:

  booting      → "Agent is starting up..." spinner
  registering  → "Registering on Moltbook..."
  registered   → Claim URL + verification code + Twitter instructions
  verified     → Normal dashboard (activity, feed, stats)
  error        → Error message + retry info
"""

import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .agent import MoltbookAgent, AgentState
from .scheduler import HeartbeatScheduler
from .attestation import get_full_attestation


log = structlog.get_logger()

# Global instances
agent: Optional[MoltbookAgent] = None
scheduler: Optional[HeartbeatScheduler] = None


# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    global agent, scheduler

    # Startup
    log.info("Starting SecretMolt agent...")

    agent = MoltbookAgent()
    await agent.initialize()

    scheduler = HeartbeatScheduler(agent.heartbeat)
    await scheduler.start()

    log.info("Agent started successfully", state=agent.state)

    yield

    # Shutdown
    log.info("Shutting down...")
    scheduler.stop()
    await agent.close()
    log.info("Shutdown complete")


# ============ App Setup ============

app = FastAPI(
    title="SecretMolt Agent API",
    description="Privacy-preserving Moltbook agent running in SecretVM",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Request/Response Models ============

class StatusResponse(BaseModel):
    """State-aware status response. Dashboard renders based on 'state' field."""
    state: str  # booting | registering | registered | verified | error

    # Always present
    agent_name: str
    model: str
    online: bool

    # Present when state == "registered" (onboarding)
    claim_url: Optional[str] = None
    verification_code: Optional[str] = None
    message: Optional[str] = None

    # Present when state == "error"
    error: Optional[str] = None

    # Present when state == "verified" (normal operation)
    paused: Optional[bool] = None
    karma: Optional[int] = None
    stats: Optional[dict] = None
    last_heartbeat: Optional[str] = None
    next_heartbeat: Optional[str] = None


# ============ Endpoints ============

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """
    Get agent status. The 'state' field drives the dashboard view.

    Dashboard logic:
      state == "booting"     → show spinner
      state == "registering" → show "Registering..."
      state == "registered"  → show claim_url, verification_code, instructions
      state == "verified"    → show normal dashboard
      state == "error"       → show error message
    """
    base = {
        "state": agent.state.value,
        "agent_name": settings.agent_name,
        "model": agent.llm.model,
        "online": scheduler.is_running if scheduler else False,
    }

    if agent.state == AgentState.REGISTERED:
        base["claim_url"] = agent.claim_url
        base["verification_code"] = agent.verification_code
        base["message"] = "Post the verification code on Twitter to activate your agent"
        return StatusResponse(**base)

    elif agent.state == AgentState.ERROR:
        base["error"] = agent.registration_error
        return StatusResponse(**base)

    elif agent.state == AgentState.VERIFIED:
        stats = await agent.get_stats()
        last_heartbeat = await agent.memory.get_config("last_heartbeat")
        base["paused"] = agent.paused
        base["karma"] = 0  # TODO: Fetch from Moltbook
        base["stats"] = stats
        base["last_heartbeat"] = last_heartbeat
        base["next_heartbeat"] = scheduler.next_run_time() if scheduler else None
        return StatusResponse(**base)

    else:
        # booting or registering
        return StatusResponse(**base)


@app.post("/api/check-verification")
async def check_verification():
    """
    Manually trigger a verification check.
    Call this after the human says they've posted on Twitter.
    """
    if agent.state == AgentState.VERIFIED:
        return {"verified": True, "message": "Already verified"}

    if agent.state != AgentState.REGISTERED:
        return {"verified": False, "message": f"Agent is in state: {agent.state.value}"}

    verified = await agent.check_verification()
    if verified:
        return {"verified": True, "message": "Verification confirmed! Agent is now live."}
    else:
        return {
            "verified": False,
            "message": "Not yet verified. Make sure the tweet with the verification code is posted."
        }


@app.get("/api/activity")
async def get_activity(limit: int = 20):
    """Get recent agent activity."""
    activities = await agent.memory.get_recent_activity(limit)
    return {"activities": [a.model_dump() for a in activities]}


@app.get("/api/feed")
async def get_feed(sort: str = "hot", limit: int = 25, submolt: str = None):
    """Get what the agent sees from Moltbook."""
    if agent.state != AgentState.VERIFIED or agent.moltbook is None:
        return {"posts": [], "message": "Agent not yet verified"}

    try:
        posts = await agent.moltbook.get_feed(sort=sort, limit=limit, submolt=submolt)
        annotated = []
        for post in posts:
            is_seen = await agent.memory.is_seen(post.id)
            annotated.append({
                **post.model_dump(),
                "seen": is_seen,
            })
        return {"posts": annotated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory")
async def get_memory():
    """View agent's memory/state."""
    return await agent.memory.export_state()


@app.get("/api/config")
async def get_config():
    """Get current agent configuration."""
    subscribed = await agent.memory.get_subscribed_submolts()
    return {
        "state": agent.state.value,
        "heartbeat_interval_hours": scheduler.interval_hours if scheduler else None,
        "paused": agent.paused,
        "agent_name": settings.agent_name,
        "agent_description": settings.agent_description,
        "subscribed_submolts": subscribed,
    }


@app.get("/api/attestation")
async def get_attestation():
    """
    Get TEE attestation data proving code integrity.
    """
    try:
        attestation_data = await get_full_attestation()
        return attestation_data
    except Exception as e:
        log.error("Failed to fetch attestation", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Attestation service unavailable: {str(e)}"
        )


@app.get("/api/birth-certificate")
async def get_birth_certificate():
    """
    Get the agent's birth certificate — cryptographic proof that the
    Moltbook API key was created inside the TEE.
    """
    cert = await agent.memory.get_config("birth_certificate")
    if not cert:
        raise HTTPException(
            status_code=404,
            detail="No birth certificate found. The agent may not have completed registration yet.",
        )
    return cert


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "state": agent.state.value if agent else "starting",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============ Run ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
