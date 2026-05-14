"""Resend API email service for sending payment reminders."""
import requests
from app.core.config import settings, logger


def send_email_via_resend(subject: str, to_email: str, html: str, text: str, from_email: str = None) -> None:
    """Send email using Resend API."""
    
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")
    
    if not from_email:
        from_email = settings.GMAIL_SEND_FROM_EMAIL or settings.SMTP_USERNAME or "noreply@resend.dev"
    
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "html": html,
            "text": text
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code not in [200, 201]:
            logger.error(f"Resend API error {response.status_code}: {response.text}")
            raise RuntimeError(f"Failed to send via Resend: {response.text}")
        
        logger.info(f"Email sent successfully via Resend to {to_email}")
        
    except Exception as exc:
        logger.error(f"Failed to send email via Resend: {exc}")
        raise
