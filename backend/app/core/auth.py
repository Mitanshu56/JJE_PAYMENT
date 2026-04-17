"""Authentication helpers for login and token verification."""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import time
from typing import Dict, Optional

from app.core.config import settings


def verify_credentials(username: str, password: str) -> bool:
    """Validate username and password against configured credentials."""
    expected_user = settings.AUTH_USERNAME
    expected_pass = settings.AUTH_PASSWORD
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_pass)


def _sign_payload(payload: str) -> str:
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")


def create_token(username: str) -> str:
    """Create a signed token with expiration."""
    expires_at = int(time.time()) + (settings.AUTH_TOKEN_EXPIRE_HOURS * 3600)
    payload_obj = {"sub": username, "exp": expires_at}
    payload = base64.urlsafe_b64encode(json.dumps(payload_obj).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = _sign_payload(payload)
    return f"{payload}.{signature}"


def decode_token(token: str) -> Optional[Dict]:
    """Decode and verify token signature and expiry."""
    if not token or "." not in token:
        return None

    try:
        payload_part, signature_part = token.split(".", 1)
        expected_signature = _sign_payload(payload_part)
        if not hmac.compare_digest(signature_part, expected_signature):
            return None

        padded_payload = payload_part + "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp <= int(time.time()):
            return None
        return payload
    except Exception:
        return None
