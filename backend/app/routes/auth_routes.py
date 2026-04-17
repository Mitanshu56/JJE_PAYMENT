"""Authentication API routes."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.auth import create_token, decode_token, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest):
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(payload.username)
    return {
        "status": "success",
        "token": token,
        "username": payload.username,
    }


@router.get("/me")
async def me(authorization: str | None = Header(default=None)):
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    claims = decode_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "status": "success",
        "username": claims.get("sub"),
        "expires_at": claims.get("exp"),
    }
