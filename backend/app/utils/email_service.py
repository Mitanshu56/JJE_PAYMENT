"""Email helpers for authentication notifications."""
from __future__ import annotations

from email.message import EmailMessage
from datetime import datetime, timezone
import smtplib

from app.core.config import settings, logger


def mask_email(value: str) -> str:
    """Mask an email for UI-safe display (e.g. mi******@gmail.com)."""
    if not value or "@" not in value:
        return "mi******"

    local, domain = value.split("@", 1)
    if len(local) >= 2:
        masked_local = f"{local[:2]}******"
    elif len(local) == 1:
        masked_local = f"{local[0]}******"
    else:
        masked_local = "mi******"

    return f"{masked_local}@{domain}"


def send_forgot_password_email(*, username: str) -> None:
    """Send forgot-password assistance email to configured recovery inbox."""
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP credentials are not configured")

    to_email = settings.RECOVERY_EMAIL
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    msg = EmailMessage()
    msg["Subject"] = "JJE Login - Password Reset Request"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(
        "\n".join(
            [
                "A forgot password request was received.",
                "",
                f"User ID: {username}",
                f"Requested At: {now_utc}",
                "",
                "If this was you, please contact admin or support to update the password safely.",
                "If this was not you, ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:
        logger.error(f"Failed to send forgot-password email: {exc}")
        raise
