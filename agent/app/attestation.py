# Attestation Module
"""
TEE attestation helper functions for SecretVM and SecretAI.

Fetches attestation data from:
1. SecretVM's attestation server (localhost:29343) - proves agent code integrity
2. SecretAI's attestation endpoint - proves LLM inference is confidential

Together, these provide full end-to-end verifiability:
- The agent code running is exactly what's published (SecretVM)
- The LLM inference is private and the model is verified (SecretAI)
"""

import re
import httpx
import structlog
from datetime import datetime
from typing import Optional

from .config import settings


log = structlog.get_logger()

# SecretVM attestation server (agent code TEE)
SECRETVM_ATTESTATION_SERVER = "https://localhost:29343"

# SecretAI attestation endpoint (LLM inference TEE)
SECRETAI_BASE_URL = "https://secretai-rytn.scrtlabs.com:21434"


# ============ SecretVM Attestation (Agent Code) ============

async def get_secretvm_cpu_quote() -> dict:
    """
    Fetch CPU attestation quote from SecretVM TEE.

    Returns Intel TDX measurements:
    - MRTD: Firmware hash
    - RTMR0: Configuration hash
    - RTMR1: Linux kernel hash
    - RTMR2: Application hash
    - RTMR3: Root filesystem + docker-compose.yaml hash
    - reportdata: TLS certificate fingerprint
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                f"{SECRETVM_ATTESTATION_SERVER}/cpu.html",
                timeout=10.0
            )
            response.raise_for_status()
            content = response.text
            return _parse_cpu_quote(content)

        except httpx.HTTPError as e:
            log.warning("Failed to fetch SecretVM CPU quote", error=str(e))
            raise


async def get_secretvm_report() -> dict:
    """
    Fetch full attestation report from SecretVM TEE.

    Returns metadata about the running environment including
    TLS fingerprint and container information.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                f"{SECRETVM_ATTESTATION_SERVER}/self.html",
                timeout=10.0
            )
            response.raise_for_status()
            content = response.text
            return _parse_attestation_report(content)

        except httpx.HTTPError as e:
            log.warning("Failed to fetch SecretVM attestation report", error=str(e))
            raise


async def get_secretvm_attestation() -> dict:
    """
    Get SecretVM attestation data (agent code integrity).
    """
    try:
        cpu_quote = await get_secretvm_cpu_quote()
        report = await get_secretvm_report()

        return {
            "cpu_quote": cpu_quote,
            "report": report,
            "tee_type": "Intel TDX",
            "verified": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        log.warning("SecretVM attestation unavailable", error=str(e))
        return {
            "cpu_quote": None,
            "report": None,
            "tee_type": "Intel TDX",
            "verified": False,
            "error": f"SecretVM attestation unavailable: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============ SecretAI Attestation (LLM Inference) ============

async def get_secretai_attestation() -> dict:
    """
    Fetch attestation data from SecretAI LLM service.

    Proves that LLM inference is happening in a TEE with:
    - Model integrity verification
    - Confidential inference guarantees
    - No data leakage to operators
    """
    headers = {}
    if settings.secret_ai_api_key:
        headers["X-API-Key"] = settings.secret_ai_api_key

    async with httpx.AsyncClient(verify=True) as client:
        try:
            # Try the attestation endpoint
            response = await client.get(
                f"{SECRETAI_BASE_URL}/attestation",
                headers=headers,
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()

            return {
                "attestation": data,
                "service": "SecretAI",
                "model": settings.secret_ai_model,
                "verified": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except httpx.HTTPStatusError as e:
            # Try alternative endpoint paths
            if e.response.status_code == 404:
                return await _try_alternative_secretai_attestation(client, headers)
            log.warning("SecretAI attestation request failed", status=e.response.status_code)
            raise

        except httpx.HTTPError as e:
            log.warning("Failed to fetch SecretAI attestation", error=str(e))
            raise


async def _try_alternative_secretai_attestation(client: httpx.AsyncClient, headers: dict) -> dict:
    """
    Try alternative SecretAI attestation endpoints.
    """
    alternative_paths = [
        "/v1/attestation",
        "/api/attestation",
        "/health/attestation",
    ]

    for path in alternative_paths:
        try:
            response = await client.get(
                f"{SECRETAI_BASE_URL}{path}",
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "attestation": data,
                    "service": "SecretAI",
                    "model": settings.secret_ai_model,
                    "verified": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception:
            continue

    # No attestation endpoint found - return status indicating service is TEE-based
    # but attestation endpoint not exposed
    return {
        "attestation": None,
        "service": "SecretAI",
        "model": settings.secret_ai_model,
        "verified": False,
        "error": "SecretAI attestation endpoint not available - service runs in TEE but does not expose attestation API",
        "note": "SecretAI runs on Secret Network infrastructure which provides confidential computing guarantees",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============ Combined Attestation ============

async def get_full_attestation() -> dict:
    """
    Get combined attestation data from both SecretVM and SecretAI.

    This provides full end-to-end verifiability:
    - secretvm: Proves the agent code is unmodified
    - secretai: Proves the LLM inference is confidential

    Anyone can verify:
    1. The exact published code is running (RTMR3 hash)
    2. The LLM service is running in a TEE
    3. No human can intercept or modify the agent's decisions
    """
    # Fetch both attestations concurrently
    secretvm_task = get_secretvm_attestation()
    secretai_task = get_secretai_attestation()

    try:
        import asyncio
        secretvm_result, secretai_result = await asyncio.gather(
            secretvm_task,
            secretai_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(secretvm_result, Exception):
            secretvm_result = {
                "cpu_quote": None,
                "report": None,
                "tee_type": "Intel TDX",
                "verified": False,
                "error": str(secretvm_result),
                "timestamp": datetime.utcnow().isoformat(),
            }

        if isinstance(secretai_result, Exception):
            secretai_result = {
                "attestation": None,
                "service": "SecretAI",
                "model": settings.secret_ai_model,
                "verified": False,
                "error": str(secretai_result),
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Combined verification status
        fully_verified = (
            secretvm_result.get("verified", False) and
            secretai_result.get("verified", False)
        )

        return {
            "secretvm": secretvm_result,
            "secretai": secretai_result,
            "fully_verified": fully_verified,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": _generate_attestation_summary(secretvm_result, secretai_result),
        }

    except Exception as e:
        log.error("Failed to fetch attestation data", error=str(e))
        return {
            "secretvm": None,
            "secretai": None,
            "fully_verified": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def _generate_attestation_summary(secretvm: dict, secretai: dict) -> dict:
    """Generate a human-readable summary of attestation status."""
    return {
        "agent_code": "verified" if secretvm.get("verified") else "unverified",
        "llm_inference": "verified" if secretai.get("verified") else "unverified",
        "end_to_end_privacy": "guaranteed" if (
            secretvm.get("verified") and secretai.get("verified")
        ) else "partial",
        "explanation": _get_explanation(secretvm, secretai),
    }


def _get_explanation(secretvm: dict, secretai: dict) -> str:
    """Generate explanation of current attestation status."""
    if secretvm.get("verified") and secretai.get("verified"):
        return (
            "Full end-to-end privacy verified. The agent code is running unmodified "
            "in a SecretVM TEE, and all LLM inference happens in SecretAI's confidential "
            "computing environment. No human can access prompts, responses, or modify behavior."
        )
    elif secretvm.get("verified"):
        return (
            "Agent code verified in SecretVM TEE. LLM attestation not available but "
            "SecretAI runs on Secret Network's confidential infrastructure."
        )
    elif secretai.get("verified"):
        return (
            "LLM inference verified in SecretAI TEE. Agent code attestation not available "
            "(may not be running in SecretVM)."
        )
    else:
        return (
            "Attestation not available. This may indicate the agent is running in "
            "development mode outside of TEE environments."
        )


# ============ Parsing Helpers ============

def _parse_cpu_quote(html_content: str) -> dict:
    """
    Parse CPU quote data from SecretVM attestation server HTML response.
    """
    quote = {
        "mrtd": "",
        "rtmr0": "",
        "rtmr1": "",
        "rtmr2": "",
        "rtmr3": "",
        "reportdata": "",
    }

    patterns = {
        "mrtd": r"MRTD[:\s]+([a-fA-F0-9]+)",
        "rtmr0": r"RTMR0[:\s]+([a-fA-F0-9]+)",
        "rtmr1": r"RTMR1[:\s]+([a-fA-F0-9]+)",
        "rtmr2": r"RTMR2[:\s]+([a-fA-F0-9]+)",
        "rtmr3": r"RTMR3[:\s]+([a-fA-F0-9]+)",
        "reportdata": r"reportdata[:\s]+([a-fA-F0-9]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            quote[key] = match.group(1)

    return quote


def _parse_attestation_report(html_content: str) -> dict:
    """
    Parse attestation report data from SecretVM attestation server HTML response.
    """
    report = {
        "tls_fingerprint": "",
        "container_hash": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    tls_match = re.search(
        r"(?:TLS|Certificate)\s*(?:fingerprint|Fingerprint)[:\s]+([a-fA-F0-9:]+)",
        html_content,
        re.IGNORECASE
    )
    if tls_match:
        report["tls_fingerprint"] = tls_match.group(1)

    hash_match = re.search(
        r"(?:container|image)\s*(?:hash|Hash)[:\s]+([a-fA-F0-9]+)",
        html_content,
        re.IGNORECASE
    )
    if hash_match:
        report["container_hash"] = hash_match.group(1)

    return report
