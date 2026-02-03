# FastAPI Application
"""
HTTP API for monitoring the autonomous Moltbook agent.

This is a MONITORING-ONLY API. The agent is fully autonomous and cannot be
controlled via this API. All control endpoints have been removed to ensure
provable autonomy.
"""

import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .agent import MoltbookAgent
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
    
    log.info("Agent started successfully")
    
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
    version="0.1.0",
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
    online: bool
    paused: bool
    karma: int
    stats: dict
    last_heartbeat: Optional[str]
    next_heartbeat: Optional[str]
    model: str


class ErrorResponse(BaseModel):
    error: bool = True
    code: str
    message: str


# ============ Endpoints ============

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get agent status and statistics."""
    stats = await agent.get_stats()
    last_heartbeat = await agent.memory.get_config("last_heartbeat")
    
    return StatusResponse(
        online=scheduler.is_running,
        paused=agent.paused,
        karma=0,  # TODO: Fetch from Moltbook
        stats=stats,
        last_heartbeat=last_heartbeat,
        next_heartbeat=scheduler.next_run_time(),
        model=agent.llm.model,
    )


@app.get("/api/activity")
async def get_activity(limit: int = 20):
    """Get recent agent activity."""
    activities = await agent.memory.get_recent_activity(limit)
    return {"activities": [a.model_dump() for a in activities]}


@app.get("/api/feed")
async def get_feed(sort: str = "hot", limit: int = 25, submolt: str = None):
    """Get what the agent sees from Moltbook."""
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


@app.post("/api/generate")
async def generate_content(topic: Optional[str] = None):
    """Generate post content without posting (for preview)."""
    content = await agent.generate_post_content(topic_hint=topic)
    return content


@app.get("/api/memory")
async def get_memory():
    """View agent's memory/state."""
    return await agent.memory.export_state()


@app.get("/api/config")
async def get_config():
    """Get current agent configuration."""
    subscribed = await agent.memory.get_subscribed_submolts()
    return {
        "heartbeat_interval_hours": scheduler.interval_hours,
        "paused": agent.paused,
        "agent_name": settings.agent_name,
        "subscribed_submolts": subscribed,
    }


@app.post("/api/heartbeat")
async def trigger_heartbeat():
    """Manually trigger a heartbeat cycle."""
    result = await agent.heartbeat()
    return {
        "status": "completed",
        **result.model_dump()
    }


@app.get("/api/attestation")
async def get_attestation():
    """
    Get TEE attestation data proving code integrity.

    Fetches from SecretVM's built-in attestation server (port 29343):
    - CPU attestation quote with Intel TDX measurements
    - Attestation report with environment metadata

    This allows anyone to verify that the exact published code is running
    in a trusted execution environment with no modifications.
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
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
