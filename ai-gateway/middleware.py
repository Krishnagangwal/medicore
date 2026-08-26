"""
JWT verification as a FastAPI dependency.

JWT_SECRET must match backend/.env exactly (same string, both
services) — the Node.js backend issues tokens, this gateway only
verifies them, without ever calling back into Node.js to do so.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "medicore-dev-secret-change-in-production-32chars")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "medicore-api"


async def verify_token(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency. Verifies JWT from Authorization: Bearer <token>.

    Raises 401 if missing or invalid. Returns the decoded payload.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = parts[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], issuer=JWT_ISSUER)
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def optional_token(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Same as verify_token but returns None instead of raising —
    for routes that work with or without auth."""
    if not authorization:
        return None
    try:
        return await verify_token(authorization)
    except HTTPException:
        return None
