"""Email reply notification checker service."""
import re
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class EmailReplyChecker:
    """Check for replies to payment reminder emails."""
    
    def __init__(self, email_user: str, email_password: str, imap_host: str = 'imap.gmail.com', imap_port: int = 993):
        self.email_user = email_user
        self.email_password = email_password
        self.imap_host = imap_host
        self.imap_port = imap_port
    
    def _decode_header(self, header):
        """Safely decode email headers."""
        if not header:
            return ""
        try:
            decoded_parts = decode_header(header)
            result = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(charset or 'utf-8', errors='ignore')
                else:
                    result += part or ""
            return result
        except:
            return str(header)
    
    def _extract_invoice_numbers(self, text):
        """Extract invoice numbers from text."""
        if not text:
            return []
        patterns = [
            r'\b(?:invoice(?:\s*no\.?|\s*number)?|inv(?:oice)?)\s*[#:.-]?\s*([A-Za-z0-9/-]+)\b',
            r'\bINV[-#\s]*([A-Za-z0-9/-]+)\b',
        ]
        matches: List[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        cleaned: List[str] = []
        seen = set()
        for value in matches:
            normalized = str(value).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                cleaned.append(normalized)
        return cleaned

    def _extract_thread_id(self, msg) -> str:
        """Extract a stable thread reference for a reply email."""
        return (msg.get('Message-ID', '') or msg.get('In-Reply-To', '') or msg.get('References', '') or '').strip()

    def _is_reply_subject(self, subject: str) -> bool:
        if not subject:
            return False
        return bool(re.match(r'^\s*(re|fwd)\s*:', subject, re.IGNORECASE))

    async def _get_known_party_emails(self, db: AsyncIOMotorDatabase) -> set:
        """Collect party emails we can match against."""
        emails = set()
        try:
            async for doc in db['party_contacts'].find({}, {'email': 1, 'party_name': 1}):
                if doc.get('email'):
                    emails.add(str(doc['email']).strip().lower())
            async for doc in db['parties'].find({}, {'email': 1, 'party_email': 1, 'party_name': 1, 'name': 1}):
                for key in ('email', 'party_email'):
                    value = doc.get(key)
                    if value:
                        emails.add(str(value).strip().lower())
        except Exception as exc:
            logger.warning(f'Could not load known party emails: {exc}')
        return emails
    
    def _extract_snippet(self, body, max_length=200):
        """Extract first 200 chars of email body as snippet."""
        if not body:
            return ""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', body.strip())
        return text[:max_length] + ("..." if len(text) > max_length else "")
    
    def _clean_email_body(self, body):
        """Clean email body (remove quoted text, signatures, etc.)."""
        if not body:
            return ""
        
        lines = body.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip quoted lines
            if line.strip().startswith('>'):
                continue
            # Skip signature separator
            if line.strip().startswith('--'):
                break
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def _extract_clean_reply_message(self, body: str) -> str:
        """Extract only the actual reply text, removing Gmail headers and quoted content."""
        if not body:
            return ""

        lines = body.split('\n')
        reply_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Skip quoted lines (start with >)
            if stripped.startswith('>'):
                continue

            # Skip signature separator
            if stripped.startswith('--') or stripped.startswith('__'):
                break

            # Skip Gmail forwarding header lines (On DATE... wrote:)
            if re.match(r'^\s*on\s+.*?wrote:', stripped, re.IGNORECASE):
                continue

            # Skip email header lines (From:, Sent:, To:, Subject:, Date:, etc.)
            if re.match(r'^(from|sent|to|subject|date|cc|bcc|reply-to):\s*', stripped, re.IGNORECASE):
                continue

            # Skip lines that are just email addresses
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', stripped):
                continue

            # Add this line to reply
            reply_lines.append(stripped)

        # Join and clean up
        result = ' '.join(reply_lines).strip()

        # Remove redundant spaces
        result = re.sub(r'\s+', ' ', result)

        return result
    
    def _get_email_body(self, msg):
        """Extract text body from email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = msg.get_payload()
        
        return body
    
    async def check_for_replies(self, db: AsyncIOMotorDatabase) -> dict:
        """Check IMAP inbox for payment reminder replies."""
        result = {
            'status': 'error',
            'checked_count': 0,
            'new_notifications': 0,
            'message': ''
        }
        
        try:
            # Connect to Gmail IMAP
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            imap.login(self.email_user, self.email_password)
            logger.info(f"✓ Connected to Gmail IMAP for {self.email_user}")
            
            # Select inbox
            imap.select('INBOX')
            
            status, messages = imap.search(None, 'ALL')
            if status != 'OK' or not messages or not messages[0]:
                result['status'] = 'success'
                result['message'] = 'Inbox is empty'
                return result

            email_ids = messages[0].split()
            recent_email_ids = email_ids[-50:]
            result['checked_count'] = len(recent_email_ids)

            known_party_emails = await self._get_known_party_emails(db)
            logger.info(f"Found {len(recent_email_ids)} recent emails to inspect for replies")

            for email_id in recent_email_ids:
                try:
                    status, msg_data = imap.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email fields
                    from_name, from_email = parseaddr(msg.get('From', ''))
                    from_email = (from_email or '').strip().lower()
                    subject = self._decode_header(msg.get('Subject', ''))
                    message_id = (msg.get('Message-ID', '') or '').strip()
                    reply_date_str = msg.get('Date', '')
                    
                    # Ignore outbound/system emails and non-replies
                    if not from_email or from_email == self.email_user.lower():
                        continue
                    if not self._is_reply_subject(subject) and not msg.get('In-Reply-To') and not msg.get('References'):
                        continue
                    if known_party_emails and from_email not in known_party_emails:
                        continue
                    
                    # Get email body
                    body = self._get_email_body(msg)
                    cleaned_body = self._clean_email_body(body)
                    clean_message = self._extract_clean_reply_message(body)
                    snippet = self._extract_snippet(cleaned_body)
                    
                    # Extract invoice numbers
                    invoice_numbers = self._extract_invoice_numbers(subject + " " + body)
                    
                    # Check if this message already exists (by messageId)
                    existing = await db['payment_reply_notifications'].find_one({'gmailMessageId': message_id})
                    
                    if existing:
                        logger.info(f"Notification for {message_id} already exists, skipping")
                        continue
                    
                    # Try to match party by email
                    party = await db['parties'].find_one({
                        '$or': [
                            {'email': {'$regex': f'^{re.escape(from_email)}$', '$options': 'i'}},
                            {'party_email': {'$regex': f'^{re.escape(from_email)}$', '$options': 'i'}},
                        ]
                    })
                    if not party:
                        party = await db['party_contacts'].find_one({
                            'email': {'$regex': f'^{re.escape(from_email)}$', '$options': 'i'}
                        })
                    
                    party_name = (
                        party.get('name')
                        if party and party.get('name')
                        else party.get('party_name')
                        if party and party.get('party_name')
                        else from_email
                    )

                    reply_received_at = datetime.utcnow()
                    if reply_date_str:
                        try:
                            parsed_date = parsedate_to_datetime(reply_date_str)
                            if parsed_date:
                                reply_received_at = parsed_date.replace(tzinfo=None) if parsed_date.tzinfo else parsed_date
                        except Exception:
                            pass
                    
                    # Create notification
                    notification = {
                        'type': 'payment_reply',
                        'partyName': party_name,
                        'partyEmail': from_email,
                        'invoiceNumbers': invoice_numbers,
                        'emailSubject': subject,
                        'replyMessage': cleaned_body,
                        'cleanMessage': clean_message,
                        'messageSnippet': snippet,
                        'isRead': False,
                        'replyReceivedAt': reply_received_at,
                        'gmailMessageId': message_id,
                        'threadId': self._extract_thread_id(msg),
                        'createdAt': datetime.utcnow(),
                        'updatedAt': datetime.utcnow(),
                    }
                    
                    # Insert notification
                    await db['payment_reply_notifications'].insert_one(notification)
                    result['new_notifications'] += 1
                    
                    logger.info(f"✓ Created notification from {party_name} ({from_email}) for invoices {invoice_numbers}")
                
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
            
            imap.close()
            imap.logout()
            
            result['status'] = 'success'
            result['message'] = f"Checked {result['checked_count']} emails, created {result['new_notifications']} notifications"
            logger.info(result['message'])
            
        except imaplib.IMAP4.error as e:
            result['message'] = f"IMAP error: {str(e)}"
            logger.error(result['message'])
        except Exception as e:
            result['message'] = f"Error checking email replies: {str(e)}"
            logger.error(result['message'])
        
        return result


async def check_email_replies(
    db: AsyncIOMotorDatabase,
    email_user: str,
    email_password: str,
    imap_host: str = 'imap.gmail.com',
    imap_port: int = 993,
):
    """Async wrapper to check for email replies."""
    try:
        checker = EmailReplyChecker(email_user, email_password, imap_host=imap_host, imap_port=imap_port)
        result = await checker.check_for_replies(db)
        return result
    except Exception as e:
        logger.error(f"Error in check_email_replies: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'checked_count': 0,
            'new_notifications': 0
        }
