"""Small, dependency-free API-key authentication for the demo service.

Local development remains convenient when authentication is disabled. Any
deployment marked as production must provide an API key and an admin key.
The keys are intentionally read only from the environment and compared in
constant time.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, Request


def auth_required() -> bool:
    configured = os.getenv("PHARMASTOCK_AUTH_REQUIRED")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "development").strip().lower() in {"production", "prod"}


def _actor(request: Request) -> str:
    value = request.headers.get("X-Actor-ID", "local-development").strip()
    return value[:120] or "unknown-actor"


def _check_key(provided: str | None, expected: str | None) -> bool:
    return bool(provided and expected and hmac.compare_digest(provided, expected))


def _authenticate(request: Request, *, admin: bool) -> str:
    if not auth_required():
        return _actor(request)

    api_key = request.headers.get("X-API-Key")
    admin_key = request.headers.get("X-Admin-Key")
    expected_api = os.getenv("PHARMASTOCK_API_KEY")
    expected_admin = os.getenv("PHARMASTOCK_ADMIN_KEY")
    if not expected_api or not expected_admin:
        raise HTTPException(503, "Authentication is not configured on this service")
    if admin:
        valid = _check_key(admin_key, expected_admin)
    else:
        valid = _check_key(api_key, expected_api) or _check_key(admin_key, expected_admin)
    if not valid:
        raise HTTPException(401, "A valid API key is required")
    return _actor(request)


def require_api_access(request: Request) -> str:
    return _authenticate(request, admin=False)


def require_admin_access(request: Request) -> str:
    return _authenticate(request, admin=True)

