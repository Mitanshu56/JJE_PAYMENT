"""Authentication API routes."""
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import create_token, decode_token
from app.core.config import settings, logger
from app.core.database import get_db
from app.utils.email_service import mask_email, send_forgot_password_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])
AUTH_SETTINGS_ID = "primary_auth"
RESET_TOKEN_COLLECTION = "password_reset_tokens"
PASSWORD_HISTORY_LIMIT = 5


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 200_000)
    return f"{salt_bytes.hex()}:{digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt_bytes = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 200_000)
    return hmac.compare_digest(computed, expected)


async def _get_auth_settings(db: AsyncIOMotorDatabase) -> dict:
    collection = db["auth_settings"]
    record = await collection.find_one({"_id": AUTH_SETTINGS_ID})
    if record:
        record.setdefault("password_history", [])
        return record

    seeded = {
        "_id": AUTH_SETTINGS_ID,
        "username": settings.AUTH_USERNAME,
        "password_hash": _hash_password(settings.AUTH_PASSWORD),
        "password_history": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await collection.insert_one(seeded)
    return seeded


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return "unknown date"
    return value.strftime("%d %b %Y, %I:%M %p")


def _password_history_entry(password_hash: str, changed_at: datetime) -> dict:
    return {
        "password_hash": password_hash,
        "changed_at": changed_at,
    }


def _find_password_reuse_date(password: str, auth_settings: dict) -> datetime | None:
    current_hash = str(auth_settings.get("password_hash") or "")
    updated_at = auth_settings.get("updated_at") or auth_settings.get("created_at")

    if current_hash and _verify_password(password, current_hash):
        return updated_at if isinstance(updated_at, datetime) else None

    for entry in auth_settings.get("password_history", []) or []:
        entry_hash = str(entry.get("password_hash") or "")
        if entry_hash and _verify_password(password, entry_hash):
            changed_at = entry.get("changed_at")
            return changed_at if isinstance(changed_at, datetime) else None

    return None


def _reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _create_reset_token(db: AsyncIOMotorDatabase, username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.AUTH_RESET_TOKEN_EXPIRE_HOURS)
    await db[RESET_TOKEN_COLLECTION].insert_one(
        {
            "token_hash": _reset_token_hash(token),
            "username": username,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.utcnow(),
        }
    )
    return token


async def _consume_reset_token(db: AsyncIOMotorDatabase, token: str) -> dict | None:
    token_hash = _reset_token_hash(token)
    collection = db[RESET_TOKEN_COLLECTION]
    token_doc = await collection.find_one(
        {
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()},
        }
    )
    if not token_doc:
        return None

    await collection.update_one(
        {"_id": token_doc["_id"]},
        {"$set": {"used": True, "used_at": datetime.utcnow()}},
    )
    return token_doc


def _send_forgot_password_email_safe(username: str, reset_link: str) -> None:
    """Best-effort reset email sender used by background tasks."""
    try:
        send_forgot_password_email(username=username, reset_link=reset_link)
    except Exception as exc:
        logger.error(f"Forgot-password email send failed: {exc}")


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    auth_settings = await _get_auth_settings(db)
    expected_username = str(auth_settings.get("username") or settings.AUTH_USERNAME).strip()
    password_hash = str(auth_settings.get("password_hash") or "")
    admin_username = str(settings.ADMIN_USERNAME or "").strip()
    admin_password = str(settings.ADMIN_PASSWORD or "")

    username = payload.username.strip()
    role = "user"

    if username == admin_username and hmac.compare_digest(payload.password, admin_password):
        role = "admin"
    elif username == expected_username and _verify_password(payload.password, password_hash):
        role = "user"
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(username, role=role)
    return {
        "status": "success",
        "token": token,
        "username": username,
        "role": role,
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
        "role": claims.get("role", "user"),
        "expires_at": claims.get("exp"),
    }


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    auth_settings = await _get_auth_settings(db)
    requested_username = (payload.username or auth_settings.get("username") or settings.AUTH_USERNAME).strip() or settings.AUTH_USERNAME
    reset_token = await _create_reset_token(db, requested_username)

    # Keep response generic; do not expose account validation details.
    masked_recovery_email = mask_email(settings.RECOVERY_EMAIL)
    reset_link = f"{settings.FRONTEND_BASE_URL}/?reset_token={reset_token}"

    # Queue email sending and return immediately so UI does not fail on SMTP latency.
    background_tasks.add_task(_send_forgot_password_email_safe, requested_username, reset_link)

    return {
        "status": "success",
        "message": f"Reset password link sent on {masked_recovery_email}",
        "masked_email": masked_recovery_email,
        "user_id": requested_username,
        "reset_link": reset_link,
    }


@router.get("/reset-password/validate")
async def validate_reset_password(token: str = Query(..., min_length=1), db: AsyncIOMotorDatabase = Depends(get_db)):
    token_doc = await db[RESET_TOKEN_COLLECTION].find_one(
        {
            "token_hash": _reset_token_hash(token),
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()},
        }
    )
    if not token_doc:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")

    return {
        "status": "success",
        "username": token_doc.get("username"),
        "expires_at": token_doc.get("expires_at"),
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    auth_settings = await _get_auth_settings(db)
    reused_password_date = _find_password_reuse_date(payload.password.strip(), auth_settings)
    if reused_password_date:
        raise HTTPException(
            status_code=400,
            detail=f"Your password has already been changed on {_format_datetime(reused_password_date)}. Please choose a new password.",
        )

    token_doc = await _consume_reset_token(db, payload.token)
    if not token_doc:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")

    new_password_hash = _hash_password(payload.password)
    previous_password_hash = str(auth_settings.get("password_hash") or "")
    password_history = list(auth_settings.get("password_history") or [])
    if previous_password_hash:
        password_history.insert(
            0,
            _password_history_entry(previous_password_hash, auth_settings.get("updated_at") or auth_settings.get("created_at") or datetime.utcnow()),
        )
    password_history = password_history[:PASSWORD_HISTORY_LIMIT]

    await db["auth_settings"].update_one(
        {"_id": AUTH_SETTINGS_ID},
        {
            "$set": {
                "username": token_doc.get("username") or auth_settings.get("username") or settings.AUTH_USERNAME,
                "password_hash": new_password_hash,
                "password_history": password_history,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    return {
        "status": "success",
        "message": "Password updated successfully",
        "dashboard_link": "/",
        "changed_at": datetime.utcnow(),
    }
