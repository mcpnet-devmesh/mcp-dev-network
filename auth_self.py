"""
Self-service auth: signup/login endpoints that issue JWT tokens.
Users register with email+password, get a token back instantly.
ponytail: bcrypt for passwords, no external auth provider needed.
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from jose import jwt

router = APIRouter(prefix="/auth", tags=["auth"])

# ponytail: use HMAC-SHA256 for password hashing instead of bcrypt
# to avoid adding a dependency. Ceiling: no adaptive cost factor.
# Upgrade path: switch to argon2-cffi if brute-force becomes a concern.
_PEPPER = os.environ.get("AUTH_PEPPER", "mcp-dev-network-pepper-2026")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), (salt + _PEPPER).encode(), 100_000).hex()


# --- Models ---

class SignupRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email inválido")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password debe tener mínimo 6 caracteres")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: str
    expires_in: int  # seconds


# --- Key loading ---

_private_key: str | None = None


def _get_private_key() -> str:
    global _private_key
    if _private_key is None:
        pem = os.environ.get("OAUTH_PRIVATE_KEY")
        if not pem:
            raise RuntimeError("OAUTH_PRIVATE_KEY env var required for self-service auth")
        _private_key = pem
    return _private_key


def _issue_token(user_id: str) -> TokenResponse:
    """Issue a 30-day JWT for the given user_id."""
    now = datetime.now(timezone.utc)
    exp_seconds = 30 * 24 * 3600  # 30 days
    payload = {
        "sub": user_id,
        "iss": os.environ.get("OAUTH_ISSUER", "https://mcp-dev-network.supabase.co"),
        "exp": now + timedelta(seconds=exp_seconds),
        "iat": now,
    }
    token = jwt.encode(payload, _get_private_key(), algorithm="RS256")
    return TokenResponse(token=token, user_id=user_id, expires_in=exp_seconds)


# --- Endpoints ---

@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    """Register with email+password, get JWT token back."""
    from mcp_dev_network.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if email already exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM auth_users WHERE email = $1", req.email
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email ya registrado. Usa /auth/login")

        # Create user
        user_id = f"user_{secrets.token_hex(8)}"
        salt = secrets.token_hex(16)
        pw_hash = _hash_password(req.password, salt)

        await conn.execute(
            "INSERT INTO auth_users (user_id, email, password_hash, salt) VALUES ($1, $2, $3, $4)",
            user_id, req.email, pw_hash, salt,
        )

    return _issue_token(user_id)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Login with email+password, get fresh JWT token."""
    from mcp_dev_network.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, password_hash, salt FROM auth_users WHERE email = $1",
            req.email.lower().strip(),
        )
        if not row:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        expected_hash = _hash_password(req.password, row["salt"])
        if expected_hash != row["password_hash"]:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

    return _issue_token(row["user_id"])


@router.get("/me")
async def me(request: Request):
    """Check who owns the current token."""
    from mcp_dev_network.auth import verify_token

    user_id = await verify_token(request)
    return {"user_id": user_id}
