"""Authentication and signature verification for the AuDHD runtime.

Two auth mechanisms:
1. HMAC-SHA256 signature verification for Notion webhooks
2. Bearer token auth for direct API access (/execute, /readyz)

No bandaids. No placeholder auth. Production-grade verification.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("audhd_agents.auth")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_webhook_secret() -> str:
    """Read webhook signing secret from environment. Fatal if missing."""
    secret = os.getenv("NOTION_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise ValueError(
            "NOTION_WEBHOOK_SECRET must be set. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    return secret


def get_api_keys() -> set[str]:
    """Read comma-separated API keys from environment."""
    raw = os.getenv("AUDHD_API_KEYS", "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


# ---------------------------------------------------------------------------
# HMAC-SHA256 Webhook Signature Verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(
    body: bytes,
    signature_header: Optional[str],
    secret: str,
    *,
    timestamp_header: Optional[str] = None,
    max_age_seconds: int = 300,
) -> bool:
    """Verify Notion webhook HMAC-SHA256 signature.

    Args:
        body: Raw request body bytes
        signature_header: Value of X-Notion-Signature header
        secret: Webhook signing secret
        timestamp_header: Value of X-Notion-Timestamp header (replay protection)
        max_age_seconds: Maximum age of event before rejection (default 5 min)

    Returns:
        True if signature is valid

    Raises:
        HTTPException: On invalid/missing signature or stale timestamp
    """
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Notion-Signature header",
        )

    # Replay protection: reject stale events
    if timestamp_header:
        try:
            event_time = int(timestamp_header)
            now = int(time.time())
            if abs(now - event_time) > max_age_seconds:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Event timestamp too old ({abs(now - event_time)}s > {max_age_seconds}s)",
                )
        except ValueError:
            logger.warning("Invalid timestamp header: %s", timestamp_header)

    # Compute expected signature
    # Notion format: v1=<hex_digest> or just <hex_digest>
    expected_mac = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Strip version prefix if present (e.g., "v1=abc123" -> "abc123")
    provided_sig = signature_header
    if "=" in provided_sig:
        provided_sig = provided_sig.split("=", 1)[1]

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_mac, provided_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    return True


# ---------------------------------------------------------------------------
# Bearer Token Auth for API Endpoints
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> str:
    """Verify Bearer token against configured API keys.

    Usage in FastAPI:
        @app.post("/execute", dependencies=[Depends(verify_api_key)])

    Returns the verified API key for audit logging.
    """
    api_keys = get_api_keys()

    # AUDIT-FIX: A-1 -- Fail-secure when no API keys configured
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API keys not configured",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check against all configured keys (constant-time per key)
    for key in api_keys:
        if secrets.compare_digest(token, key):
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Webhook-specific dependency
# ---------------------------------------------------------------------------

async def verify_webhook(request: Request) -> bytes:
    """FastAPI dependency: read body, verify HMAC, return raw bytes.

    Usage:
        @router.post("/webhooks/notion")
        async def handle(body: bytes = Depends(verify_webhook)):
    """
    body = await request.body()
    secret = get_webhook_secret()

    verify_webhook_signature(
        body=body,
        signature_header=request.headers.get("X-Notion-Signature"),
        secret=secret,
        timestamp_header=request.headers.get("X-Notion-Timestamp"),
    )

    return body
