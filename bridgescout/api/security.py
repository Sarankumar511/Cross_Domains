"""XSUAA JWT validation for the FastAPI backend.

On SAP BTP the HTML5 app (via the Work Zone approuter + the ``bridgescout-srv-api``
destination) forwards the end user's XSUAA access token as a bearer token. Here we
verify that token's signature against the XSUAA JWKS and check the ``Analyze``
scope.

Locally there is no ``VCAP_SERVICES`` / XSUAA binding, so auth is disabled and
every request is allowed through as an anonymous dev user. That keeps
``uvicorn bridgescout.api.app:app`` and the test suite working unchanged.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from fastapi import HTTPException, Request, status

try:  # only needed when auth is actually enabled (i.e. on BTP)
    import jwt
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover - exercised only without pyjwt installed
    jwt = None
    PyJWKClient = None


def _xsuaa_credentials() -> dict | None:
    raw = os.getenv("VCAP_SERVICES")
    if not raw:
        return None
    try:
        services = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for binding in services.get("xsuaa", []):
        credentials = binding.get("credentials")
        if credentials and credentials.get("url"):
            return credentials
    return None


_CREDENTIALS = _xsuaa_credentials()
AUTH_ENABLED = _CREDENTIALS is not None
_XSAPPNAME = (_CREDENTIALS or {}).get("xsappname", "bridgescout")
_REQUIRED_SCOPE = f"{_XSAPPNAME}.Analyze"
# Curator scope: gates the paper library (list / view / upload-persist / delete).
_ADMIN_SCOPE = f"{_XSAPPNAME}.Admin"

if AUTH_ENABLED and jwt is None:  # pragma: no cover
    raise RuntimeError(
        "XSUAA is bound but PyJWT is missing - add 'pyjwt[crypto]' to requirements.txt"
    )


@lru_cache(maxsize=1)
def _jwk_client() -> "PyJWKClient":
    token_keys_url = _CREDENTIALS["url"].rstrip("/") + "/token_keys"
    return PyJWKClient(token_keys_url)


def _decode(token: str) -> dict:
    signing_key = _jwk_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        # XSUAA audiences carry instance suffixes ("bridgescout!t123"); we check
        # the app name against the audience / scopes manually below instead.
        options={"verify_aud": False},
    )


def _scopes(claims: dict) -> list[str]:
    raw = claims.get("scope") or []
    return raw.split() if isinstance(raw, str) else list(raw)


def is_admin_claims(claims: dict | None) -> bool:
    """True when the claims carry the Admin scope, or when auth is disabled (local dev)."""
    if claims is None:
        return False
    if claims.get("auth") == "disabled":
        return True
    return _ADMIN_SCOPE in _scopes(claims)


async def optional_auth(request: Request) -> dict | None:
    """Like require_auth but never raises: returns claims, or None for an anonymous caller.

    Used by GET /api/me so the frontend can ask 'who am I' without a 401.
    """
    if not AUTH_ENABLED:
        return {"sub": "local-dev", "scope": [_REQUIRED_SCOPE, _ADMIN_SCOPE], "auth": "disabled"}
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        return _decode(header.split(" ", 1)[1].strip())
    except Exception:  # jwt.PyJWTError + JWKS/network errors
        return None


async def require_auth(request: Request) -> dict:
    """FastAPI dependency: 401 without a valid token, 403 without the Analyze scope."""
    if not AUTH_ENABLED:
        return {"sub": "local-dev", "scope": [_REQUIRED_SCOPE, _ADMIN_SCOPE], "auth": "disabled"}

    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        claims = _decode(header.split(" ", 1)[1].strip())
    except Exception as exc:  # jwt.PyJWTError + JWKS/network errors
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    if _REQUIRED_SCOPE not in _scopes(claims):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Token is missing required scope '{_REQUIRED_SCOPE}'",
        )
    return claims


async def require_admin(request: Request) -> dict:
    """FastAPI dependency for curator-only routes: require_auth, then the Admin scope."""
    claims = await require_auth(request)
    if not AUTH_ENABLED:
        return claims
    if _ADMIN_SCOPE not in _scopes(claims):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Token is missing required scope '{_ADMIN_SCOPE}'",
        )
    return claims
