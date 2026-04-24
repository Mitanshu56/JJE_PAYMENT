"""Authentication API routes."""
import asyncio
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.auth import create_token, decode_token, verify_credentials
from app.core.config import settings
from app.utils.email_service import mask_email, send_forgot_password_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str | None = None


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


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    requested_username = (payload.username or settings.AUTH_USERNAME).strip() or settings.AUTH_USERNAME

    # Keep response generic; do not expose account validation details.
    masked_recovery_email = mask_email(settings.RECOVERY_EMAIL)

    try:
        await asyncio.to_thread(send_forgot_password_email, username=requested_username)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to send reset password mail right now. Please try again.",
        )

    return {
        "status": "success",
        "message": f"Reset password mail sent on {masked_recovery_email}",
        "masked_email": masked_recovery_email,
        "user_id": requested_username,
    }
