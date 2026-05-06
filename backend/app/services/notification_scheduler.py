"""Notification scheduler - checks for email replies periodically."""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from app.services.email_reply_checker import check_email_replies
from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_notification_checker_loop(db: AsyncIOMotorDatabase):
    """
    Run notification checker loop every 5 minutes.
    Checks for payment reminder email replies.
    """
    logger.info("🔔 Starting payment notification checker loop (every 5 minutes)...")
    
    # Wait 5 minutes before first check
    await asyncio.sleep(300)
    
    while True:
        try:
            logger.info(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Checking for email replies...")
            
            # Get Gmail inbox credentials from settings
            email_user = settings.EMAIL_USER or settings.SMTP_USERNAME
            email_password = settings.EMAIL_PASS or settings.SMTP_PASSWORD
            imap_host = settings.IMAP_HOST or 'imap.gmail.com'
            imap_port = settings.IMAP_PORT or 993
            
            if not email_user or not email_password:
                logger.warning("Gmail inbox credentials not configured, skipping notification check")
                await asyncio.sleep(300)
                continue
            
            # Check for email replies
            result = await check_email_replies(db, email_user, email_password, imap_host=imap_host, imap_port=imap_port)
            
            if result['status'] == 'success':
                logger.info(f"✓ Notification check completed: {result['message']}")
            else:
                logger.warning(f"⚠ Notification check failed: {result['message']}")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in notification checker loop: {e}")
            # Wait 5 minutes before retry on error
            try:
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                logger.info("Notification checker loop cancelled")
                break
