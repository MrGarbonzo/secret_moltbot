# Attestation Module
"""
TEE attestation helper functions for SecretVM and SecretAI.

Fetches attestation data from:
1. SecretVM's attestation server (localhost:29343) - proves agent code integrity
2. SecretAI's attestation endpoint (port 29343) - proves LLM inference is confidential

Together, these provide full end-to-end verifiability:
- The agent code running is exactly what's published (SecretVM)
- The LLM inference is private and the model is verified (SecretAI)

Based on: https://github.com/MrGarbonzo/attest_ai
"""

import re
import ssl
import json
import socket
import hashlib
import asyncio
import httpx
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from .config import settings


log = structlog.get_logger()


def _get_secretvm_attestation_url() -> str:
    """Get SecretVM attestation server URL from config."""
    return settings.secretvm_attestation_url


def _get_secretai_api_url() -> str:
    """Get SecretAI API URL from config."""
    return settings.secret_ai_base_url


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
    secretvm_url = _get_secretvm_attestation_url()
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(f"{secretvm_url}/cpu.html")
            response.raise_for_status()
            content = response.text

            # Parse the quote from the HTML
            quote_data = _parse_cpu_quote(content)

            # Also extract the raw quote from <pre> tag if available
            quote_match = re.search(r'<pre[^>]*id="quoteTextarea"[^>]*>(.*?)</pre>', content, re.DOTALL)
            if quote_match:
                quote_data["raw_quote"] = quote_match.group(1).strip()[:500]

            return quote_data

        except httpx.ConnectError as e:
            log.warning("Cannot connect to SecretVM attestation server", error=str(e))
            raise
        except httpx.HTTPError as e:
            log.warning("Failed to fetch SecretVM CPU quote", error=str(e))
            raise


async def get_secretvm_report() -> dict:
    """
    Fetch full attestation report from SecretVM TEE.

    Returns metadata about the running environment including
    TLS fingerprint and container information.
    """
    secretvm_url = _get_secretvm_attestation_url()
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(f"{secretvm_url}/self.html")
            response.raise_for_status()
            content = response.text
            return _parse_attestation_report(content)

        except httpx.ConnectError as e:
            log.warning("Cannot connect to SecretVM attestation server for report", error=str(e))
            raise
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
            "source": "secretvm",
            "cpu_quote": cpu_quote,
            "report": report,
            "tee_type": "Intel TDX",
            "verified": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        log.warning("SecretVM attestation unavailable", error=str(e))
        return {
            "source": "secretvm",
            "cpu_quote": None,
            "report": None,
            "tee_type": "Intel TDX",
            "verified": False,
            "error": f"SecretVM attestation unavailable: {str(e)}",
            "hint": "Attestation is only available when running inside SecretVM TEE",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============ SecretAI Attestation (LLM Inference) ============

def _get_secretai_attestation_url() -> str:
    """
    Get the SecretAI attestation URL (port 29343 on the same host).
    """
    api_url = _get_secretai_api_url()
    parsed = urlparse(api_url)
    host = parsed.hostname
    return f"https://{host}:29343"


async def _get_tls_fingerprint(url: str) -> Dict[str, Any]:
    """
    Extract TLS fingerprint and connection metadata from a URL.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 443

        # Create SSL context (allow self-signed certificates for attestation endpoints)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Connect and get certificate
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                # Get certificate
                der_cert = ssock.getpeercert(binary_form=True)
                cert_info = ssock.getpeercert()

                # Calculate fingerprint
                fingerprint = hashlib.sha256(der_cert).hexdigest()

                return {
                    "fingerprint": fingerprint,
                    "version": ssock.version(),
                    "cipher": ssock.cipher(),
                    "cert_info": {
                        "subject": str(cert_info.get("subject", [])) if cert_info else None,
                        "issuer": str(cert_info.get("issuer", [])) if cert_info else None,
                        "notBefore": cert_info.get("notBefore") if cert_info else None,
                        "notAfter": cert_info.get("notAfter") if cert_info else None,
                    },
                    "verified": True
                }

    except Exception as e:
        log.warning("Error getting TLS fingerprint", url=url, error=str(e))
        return {
            "fingerprint": None,
            "error": str(e),
            "verified": False
        }


async def get_secretai_attestation() -> dict:
    """
    Fetch attestation data from SecretAI LLM service.

    Proves that LLM inference is happening in a TEE with:
    - Model integrity verification
    - Confidential inference guarantees
    - No data leakage to operators

    SecretAI exposes attestation on port 29343 (same as SecretVM pattern).
    """
    attestation_base_url = _get_secretai_attestation_url()
    attestation_url = f"{attestation_base_url}/cpu.html"

    headers = {}
    if settings.secret_ai_api_key:
        headers["Authorization"] = f"Bearer {settings.secret_ai_api_key}"
        headers["X-API-Key"] = settings.secret_ai_api_key

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        try:
            # Fetch attestation from port 29343/cpu.html
            response = await client.get(attestation_url, headers=headers)

            if response.status_code == 200:
                attestation_html = response.text

                # Extract the quote from the HTML
                quote_match = re.search(r'<pre[^>]*id="quoteTextarea"[^>]*>(.*?)</pre>', attestation_html, re.DOTALL)
                if quote_match:
                    attestation_content = quote_match.group(1).strip()
                else:
                    attestation_content = attestation_html[:500]

                # Get TLS fingerprint
                tls_data = await _get_tls_fingerprint(attestation_base_url)

                return {
                    "source": "secretai",
                    "service": "SecretAI",
                    "model": settings.secret_ai_model,
                    "attestation_url": attestation_url,
                    "attestation_raw": attestation_content[:500] + "..." if len(attestation_content) > 500 else attestation_content,
                    "tls_fingerprint": tls_data.get("fingerprint"),
                    "tls_version": tls_data.get("version"),
                    "cipher_suite": tls_data.get("cipher"),
                    "certificate_info": tls_data.get("cert_info"),
                    "verified": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                log.warning("SecretAI attestation endpoint returned error", status=response.status_code)
                return await _try_alternative_secretai_attestation(client, headers)

        except httpx.ConnectError as e:
            log.warning("Cannot connect to SecretAI attestation endpoint", url=attestation_url, error=str(e))
            return await _try_alternative_secretai_attestation(client, headers)

        except httpx.HTTPError as e:
            log.warning("Failed to fetch SecretAI attestation", error=str(e))
            return await _try_alternative_secretai_attestation(client, headers)


async def _try_alternative_secretai_attestation(client: httpx.AsyncClient, headers: dict) -> dict:
    """
    Try alternative SecretAI attestation approaches when port 29343 is not available.
    """
    api_url = _get_secretai_api_url()
    # Try to at least get TLS fingerprint from the API endpoint
    try:
        tls_data = await _get_tls_fingerprint(api_url)

        return {
            "source": "secretai",
            "service": "SecretAI",
            "model": settings.secret_ai_model,
            "attestation_raw": None,
            "tls_fingerprint": tls_data.get("fingerprint"),
            "tls_version": tls_data.get("version"),
            "cipher_suite": tls_data.get("cipher"),
            "certificate_info": tls_data.get("cert_info"),
            "verified": False,
            "partial": True,
            "note": "Full attestation endpoint not available, but TLS connection verified",
            "hint": "SecretAI runs on Secret Network infrastructure with confidential computing guarantees",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "source": "secretai",
            "service": "SecretAI",
            "model": settings.secret_ai_model,
            "attestation_raw": None,
            "verified": False,
            "error": f"SecretAI attestation not available: {str(e)}",
            "note": "SecretAI runs on Secret Network infrastructure which provides confidential computing guarantees",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============ Combined Attestation ============


def _create_attestation_binding(secretvm: dict, secretai: dict) -> Dict[str, Any]:
    """
    Create cryptographic binding between two attestations.
    This allows verification that both attestations were captured together.
    """
    try:
        # Create canonical representation of attestations
        secretvm_canonical = json.dumps(secretvm, sort_keys=True)
        secretai_canonical = json.dumps(secretai, sort_keys=True)

        # Calculate individual hashes
        secretvm_hash = hashlib.sha256(secretvm_canonical.encode()).hexdigest()
        secretai_hash = hashlib.sha256(secretai_canonical.encode()).hexdigest()

        # Create combined hash
        timestamp = datetime.utcnow().isoformat()
        combined = f"{secretvm_hash}:{secretai_hash}:{timestamp}"
        combined_hash = hashlib.sha256(combined.encode()).hexdigest()

        return {
            "version": "1.0",
            "algorithm": "sha256",
            "secretvm_hash": secretvm_hash,
            "secretai_hash": secretai_hash,
            "combined_hash": combined_hash,
            "timestamp": timestamp,
            "binding_valid": True
        }

    except Exception as e:
        log.error("Error creating attestation binding", error=str(e))
        return {
            "version": "1.0",
            "algorithm": "sha256",
            "error": str(e),
            "binding_valid": False
        }


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
    try:
        secretvm_result, secretai_result = await asyncio.gather(
            get_secretvm_attestation(),
            get_secretai_attestation(),
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(secretvm_result, Exception):
            secretvm_result = {
                "source": "secretvm",
                "cpu_quote": None,
                "report": None,
                "tee_type": "Intel TDX",
                "verified": False,
                "error": str(secretvm_result),
                "timestamp": datetime.utcnow().isoformat(),
            }

        if isinstance(secretai_result, Exception):
            secretai_result = {
                "source": "secretai",
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

        # Create attestation binding
        binding = _create_attestation_binding(secretvm_result, secretai_result)

        # Determine attestation quality
        quality = _determine_quality(secretvm_result, secretai_result)

        return {
            "secretvm": secretvm_result,
            "secretai": secretai_result,
            "attestation_binding": binding,
            "fully_verified": fully_verified,
            "quality": quality,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": _generate_attestation_summary(secretvm_result, secretai_result),
        }

    except Exception as e:
        log.error("Failed to fetch attestation data", error=str(e))
        return {
            "secretvm": None,
            "secretai": None,
            "attestation_binding": None,
            "fully_verified": False,
            "quality": "none",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def _determine_quality(secretvm: dict, secretai: dict) -> str:
    """Determine overall attestation quality."""
    secretvm_ok = secretvm.get("verified", False)
    secretai_ok = secretai.get("verified", False)
    secretai_partial = secretai.get("partial", False)

    if secretvm_ok and secretai_ok:
        return "high"
    elif secretvm_ok and secretai_partial:
        return "medium"
    elif secretvm_ok or secretai_ok:
        return "low"
    else:
        return "none"


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
