"""OAuth 2.1 middleware — validates JWT Bearer tokens (RS256).

Supports two key sources (checked in order):
1. OAUTH_PUBLIC_KEY env var — PEM-encoded RSA public key
2. OAUTH_JWKS_URL env var — JWKS endpoint (fetched once at first use)

Requires OAUTH_ISSUER env var for issuer validation.
"""

import os
from typing import Optional

from fastapi import HTTPException, Request
from jose import JWTError, jwt

# ponytail: lazy-loaded globals; no class needed for a single dependency function.
_public_key: Optional[str] = None
_jwks: Optional[dict] = None
_issuer: Optional[str] = None
_keys_loaded: bool = False


def _load_keys() -> None:
    """Load signing keys from environment. Called once on first token verification."""
    global _public_key, _jwks, _issuer, _keys_loaded

    _issuer = os.environ.get("OAUTH_ISSUER")
    if not _issuer:
        raise RuntimeError("OAUTH_ISSUER environment variable is required")

    # Option 1: PEM public key directly
    pem = os.environ.get("OAUTH_PUBLIC_KEY")
    if pem:
        _public_key = pem
        _keys_loaded = True
        return

    # Option 2: JWKS URL — fetch once
    jwks_url = os.environ.get("OAUTH_JWKS_URL")
    if jwks_url:
        import httpx  # ponytail: only imported if JWKS needed; dev dep doubles as runtime here

        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks = resp.json()
        _keys_loaded = True
        return

    raise RuntimeError(
        "Either OAUTH_PUBLIC_KEY or OAUTH_JWKS_URL environment variable is required"
    )


def _get_signing_key(token: str) -> str | dict:
    """Return the key material for verifying the token."""
    if _public_key:
        return _public_key
    # JWKS case — python-jose handles kid matching internally
    return _jwks  # type: ignore[return-value]


async def verify_token(request: Request) -> str:
    """FastAPI dependency: validate Bearer JWT, return user_id (sub claim).

    Raises HTTPException(401) on ANY failure — no internal details exposed.
    """
    global _keys_loaded
    if not _keys_loaded:
        try:
            _load_keys()
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")

    # Extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header[7:]  # strip "Bearer "
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        key = _get_signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"require_exp": True, "require_sub": True},
            issuer=_issuer,
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    return user_id
