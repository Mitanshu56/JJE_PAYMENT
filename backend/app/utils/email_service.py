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


def send_forgot_password_email(*, username: str, reset_link: str) -> None:
    """Send forgot-password assistance email to configured recovery inbox."""
    smtp_username = (settings.SMTP_USERNAME or "").strip()
    smtp_password = (settings.SMTP_PASSWORD or "").replace(" ", "")

    if not smtp_username or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    to_email = settings.RECOVERY_EMAIL
    from_email = (settings.SMTP_FROM_EMAIL or smtp_username).strip()

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    msg = EmailMessage()
    msg["Subject"] = "JJE Login - Password Reset Link"
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
                "Open the password reset page using the link below and set a new password.",
                reset_link,
                "",
                "If this was not you, ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.error(f"Failed to send forgot-password email: {exc}")
        raise
