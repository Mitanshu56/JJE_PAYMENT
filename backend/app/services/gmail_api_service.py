"""Gmail API email service for sending payment reminders and auth emails."""
from base64 import urlsafe_b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth
from googleapiclient.discovery import build

from app.core.config import settings, logger


GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def _get_gmail_service():
    """Get authenticated Gmail API service."""
    
    # Try service account credentials first (preferred for Render)
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=GMAIL_SCOPES
            )
            return build('gmail', 'v1', credentials=credentials)
        except Exception as exc:
            logger.warning(f"Could not load service account credentials: {exc}")
    
    # Fall back to OAuth 2.0 user credentials
    if settings.GOOGLE_REFRESH_TOKEN and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        try:
            credentials = UserCredentials(
                None,
                refresh_token=settings.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            # Refresh token if needed
            request = Request()
            if not credentials.valid:
                credentials.refresh(request)
            
            return build('gmail', 'v1', credentials=credentials)
        except Exception as exc:
            logger.error(f"Could not load OAuth2 credentials: {exc}")
            raise RuntimeError("Gmail API credentials not properly configured")
    
    raise RuntimeError("No Gmail API credentials configured. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_REFRESH_TOKEN")


def send_email_via_gmail_api(subject: str, to_email: str, html: str, text: str, from_email: str = None) -> None:
    """Send email using Gmail API."""
    try:
        service = _get_gmail_service()
        
        if not from_email:
            from_email = settings.GMAIL_SEND_FROM_EMAIL or settings.SMTP_USERNAME
        
        # Create MIME message
        message = MIMEMultipart('alternative')
        message['subject'] = subject
        message['to'] = to_email
        message['from'] = from_email
        
        # Attach text and HTML parts
        message.attach(MIMEText(text, 'plain'))
        message.attach(MIMEText(html, 'html'))
        
        # Encode message
        raw_message = urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send via Gmail API
        send_message = {'raw': raw_message}
        service.users().messages().send(userId='me', body=send_message).execute()
        
        logger.info(f"Email sent successfully via Gmail API to {to_email}")
        
    except Exception as exc:
        logger.error(f"Failed to send email via Gmail API: {exc}")
        raise
