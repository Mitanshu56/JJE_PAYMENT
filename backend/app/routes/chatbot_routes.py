"""
Chatbot Routes - FastAPI endpoints for RAG chatbot with Intent Block routing
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.rag_service import rag_service, get_llm_client
from app.services.vector_store_service import vector_store
from app.services.intent_block_service import (
    IntentBlockService, normalize_message, classify_intent, 
    get_intent_config, extract_party, extract_month, INTENT_BLOCK, SYNONYMS
)
from app.core.database import get_db
from typing import Any
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except Exception:
    AsyncIOMotorDatabase = Any
from app.core.config import settings, logger
import os
import calendar
import re
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = None
    process = None

# LLM client is provided by the RAG service via get_llm_client()

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    include_context: bool = False

class ChatResponse(BaseModel):
    response: str
    context_summary: Optional[dict] = None
    tokens_used: Optional[int] = None

class IndexRequest(BaseModel):
    fiscal_year: str


class TrainRequest(BaseModel):
    fiscal_year: str


class TrainResponse(BaseModel):
    status: str
    fiscal_year: str
    indexed: Dict[str, int]


class IndexStatusResponse(BaseModel):
    status: str
    fiscal_year: Optional[str] = None
    total_indexed_documents: int
    document_type_breakdown: Dict[str, int]
    fiscal_year_breakdown: Dict[str, int]
    sample_metadata: Optional[List[dict]] = None

class IndexResponse(BaseModel):
    status: str
    count: int
    message: str

class HistoryResponse(BaseModel):
    messages: List[dict]


MONTH_NAME_LOOKUP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}

PENDING_STATUS_SET = {'PENDING', 'UNPAID', 'PARTIAL'}
PAID_STATUS_SET = {'PAID'}


def _parse_month_and_year(message: str) -> tuple[int | None, int | None]:
    text = (message or '').lower()

    # Numeric formats like 05/2025, 5-2025, 05-25.
    numeric_match = re.search(r'\b(0?[1-9]|1[0-2])\s*[/.-]\s*(\d{2,4})\b', text)
    if numeric_match:
        month = int(numeric_match.group(1))
        year = int(numeric_match.group(2))
        if year < 100:
            year += 2000
        return month, year

    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    year = int(year_match.group(1)) if year_match else None

    month = None
    for name, value in MONTH_NAME_LOOKUP.items():
        if re.search(rf'\b{name}\b', text):
            month = value
            break

    return month, year


def extract_month_year(message: str, fiscal_year: str | None) -> tuple[int | int | None, int | None]:
    """Return (month, year) resolved against fiscal_year when possible.
    Supports names (december), numeric, 'this month', 'last month'."""
    text = (message or '').lower()
    # 'this month' / 'last month'
    if 'this month' in text:
        now = datetime.utcnow()
        return now.month, _year_for_month_in_fiscal_year(now.month, fiscal_year) or now.year
    if 'last month' in text:
        now = datetime.utcnow()
        last_month = now.month - 1 or 12
        year = now.year if now.month != 1 else now.year - 1
        # resolve with fiscal year mapping
        return last_month, _year_for_month_in_fiscal_year(last_month, fiscal_year) or year

    month, year = _parse_month_and_year(message)
    if month and (year is None):
        year = _year_for_month_in_fiscal_year(month, fiscal_year) or datetime.utcnow().year
    return month, year


def build_pending_filter(base_filter: dict) -> dict:
    return {
        **(base_filter or {}),
        '$or': [
            {'status': {'$regex': r'^(PENDING|UNPAID|PARTIALLY_PAID|PARTIAL|OVERDUE|DUE)$', '$options': 'i'}},
            {'remaining_amount': {'$gt': 0}}
        ]
    }


def _extract_bill_gst_total(doc: dict) -> float | None:
    """Return the GST total for a bill document, or None if no GST fields exist."""
    values = []
    for key in ('gst', 'gst_amount', 'total_gst'):
        value = doc.get(key)
        if value not in (None, '', 0, 0.0):
            try:
                values.append(float(value))
            except Exception:
                pass

    for key in ('cgst', 'sgst', 'igst'):
        value = doc.get(key)
        if value not in (None, '', 0, 0.0):
            try:
                values.append(float(value))
            except Exception:
                pass

    if not values:
        return None
    return sum(values)


def _normalize_status_filters(message: str) -> set[str] | None:
    text = (message or '').lower()
    if any(word in text for word in ['pending', 'outstanding', 'unpaid', 'balance due', 'due bills']):
        return PENDING_STATUS_SET
    if any(word in text for word in ['paid', 'settled', 'received']):
        return PAID_STATUS_SET
    if 'partial' in text:
        return {'PARTIAL'}
    return None


def _looks_like_structured_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'bill', 'invoice', 'payment', 'paid', 'pending', 'overdue', 'outstanding',
        'due', 'total', 'sum', 'how many', 'count', 'month', 'may', 'june', 'july',
        'statement', 'deposit', 'credit', 'bank statement'
    ])


def _next_month_start(year: int, month: int) -> datetime:
    if month == 12:
        return datetime(year + 1, 1, 1)
    return datetime(year, month + 1, 1)


def _format_money(amount: float | int | None) -> str:
    return f"${float(amount or 0):,.2f}"


def _year_for_month_in_fiscal_year(month: int, fiscal_year: str | None) -> int | None:
    """Resolve a month-only query against the active fiscal year."""
    if not fiscal_year:
        return None

    match = re.search(r'FY-(\d{4})-(\d{4})', fiscal_year)
    if not match:
        return None

    start_year = int(match.group(1))
    end_year = int(match.group(2))
    if month >= 4:
        return start_year
    return end_year


def _is_count_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'how many',
        'count',
        'number of',
        'total number',
        'total no',
        'no of',
        'how much',
    ])


def _is_invoice_count_query(message: str) -> bool:
    text = (message or '').lower()
    return _is_count_query(message) and any(word in text for word in ['bill', 'invoice', 'invoices', 'bills'])


def _is_pending_amount_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'pending amount',
        'outstanding amount',
        'balance due',
        'amount due',
        'remaining amount',
        'total pending',
        'pending total',
    ])


def _is_total_billed_amount_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'total billed amount',
        'grand total',
        'total invoice amount',
        'billing amount',
        'total amount of invoices',
        'invoice amount',
    ])


def _is_payment_history_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'payment history',
        'payments history',
        'payment made',
        'payments made',
        'paid history',
        'payment list',
        'show payments',
    ])


def _is_statement_query(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in [
        'statement',
        'bank statement',
        'statement rows',
        'deposit',
        'credited',
        'credit entries',
    ])


def _extract_party_name(message: str) -> str | None:
    """Extract a client/party name from common billing question phrasing.

    Tries multiple common patterns and cleans common stopwords so company
    names are preserved. Returns cleaned party name or None.
    """
    text = (message or '').strip()
    lowered = text.lower()

    # Common anchored patterns - try to find explicit party name after keywords
    patterns = [
        r'(?:client name|party name|party|customer name)\s*[:\-]?\s*(.+)$',
        r'(?:invoices|bills)\s+(?:of|for)\s+([A-Za-z][A-Za-z0-9&.,()\-/ ]{2,})$',
        r'(?:for)\s+([A-Za-z][A-Za-z0-9&.,()\-/ ]{2,})$',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            party = match.group(1).strip()
            party = re.sub(r'\s+', ' ', party)
            party = party.rstrip('?.!,')
            # Filter out pure stopwords and global query keywords
            if len(party) >= 3 and party.lower() not in {
                'the', 'a', 'an', 'pending', 'bills', 'invoices', 
                'payments', 'this year', 'this fiscal year', 'month'
            }:
                # Strip leading stopwords like "client", "pending", etc.
                party = re.sub(r'^(?:client|the|pending|bills|invoices)\s+', '', party, flags=re.IGNORECASE)
                if len(party) >= 2:
                    return party

    # If the message contains an explicit client/party marker but the regex did
    # not cleanly capture the value, treat the tail of the sentence as the name.
    for marker in ['client name', 'party name', 'customer name']:
        if marker in lowered:
            tail = text[lowered.rfind(marker) + len(marker):].strip(' :-,?.!')
            tail = re.sub(r'\s+', ' ', tail)
            if len(tail) >= 3:
                # strip common leading/trailing stopwords
                tail = re.sub(r'^(?:for|of|the|show|give|me|show\s+in)\s+', '', tail, flags=re.IGNORECASE)
                tail = re.sub(r'\s+(?:in|this fiscal year|fiscal year)$', '', tail, flags=re.IGNORECASE)
                return tail

    # Try to capture other phrasing forms
    patterns2 = [
        r'pending amount for\s+(.+)$',
        r'how many (?:bills|invoices) (?:of|for)\s+(.+)$',
        r'payment history of\s+(.+)$',
        r'outstanding balance for\s+(.+)$',
        r'show invoices for (?:client name\s*)?(.+)$',
        r'^(?:show|list|give)\s+(?:invoices|bills|payments)\s+(?:for|of)\s+(.+)$',
    ]
    for pattern in patterns2:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().rstrip('?.!,')
            candidate = re.sub(r'\s+', ' ', candidate)
            candidate = re.sub(r'^(?:for|of|the|show|give|me|client)\s+', '', candidate, flags=re.IGNORECASE)
            if len(candidate) >= 2 and candidate.lower() not in {
                'pending', 'bills', 'invoices', 'payments', 'this month', 'this year'
            }:
                return candidate

    return None


def normalize_party_name(name: str) -> str:
    """Normalize party/client name for matching: lowercase, remove punctuation,
    collapse company suffixes, and trim spaces."""
    if not name:
        return ''
    
    s = name.lower().strip()
    
    # Remove common company suffixes FIRST (before removing punctuation)
    # Order matters: longer patterns first, use | for alternation to handle with/without dots
    suffixes = [
        r'\bprivate\s+limited\b',
        r'\bpvt\.?\s+ltd\.?\b',
        r'\bpvt\s+limited\b',
        r'\bprivate\b',
        r'\blimited\b',
        r'\bpvt\.?\b',
        r'\bltd\.?\b',
        r'\bllp\b',
        r'\binc\.?\b',
        r'\bcorp(?:oration)?\b',
        r'\bco\.?\b',
    ]
    
    for pattern in suffixes:
        s = re.sub(pattern, '', s)
    
    # Remove all punctuation and normalize spaces
    s = re.sub(r'[^a-z0-9\s]', '', s)
    
    # Collapse multiple spaces and trim
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s


async def fuzzy_match_party(db: AsyncIOMotorDatabase, party_name: str, fiscal_year: str | None = None, candidate_names: list | None = None) -> tuple[str | None, int, list]:
    """Attempt to fuzzy-match `party_name` against candidate names.
    Returns (best_match_or_None, score, top_candidates_list).
    If `candidate_names` is provided, use it instead of querying DB.
    """
    logger.debug('Fuzzy match party: %s (fy=%s)', party_name, fiscal_year)
    if not party_name:
        return None, 0, []
    # load candidate names
    candidates = []
    if candidate_names is not None:
        candidates = candidate_names
    else:
        q = {}
        if fiscal_year:
            q = {'fiscal_year': fiscal_year}
        # gather distinct party_name values from bills and payments
        try:
            bills_names = await db['bills'].distinct('party_name', q)
            payments_names = await db['payments'].distinct('party_name', q)
            candidates = list({n for n in (bills_names or []) + (payments_names or []) if n})
        except Exception:
            candidates = []

    if not candidates:
        return None, 0, []

    # Normalize both sides for comparison but keep original label for return
    norm_target = normalize_party_name(party_name)
    scored: list[tuple[str,int]] = []
    if fuzz is None:
        # rapidfuzz not available — fallback to simple substring match
        for c in candidates:
            if not c: continue
            if norm_target in normalize_party_name(c):
                scored.append((c, 100))
    else:
        for c in candidates:
            if not c: continue
            score = int(fuzz.token_set_ratio(norm_target, normalize_party_name(c)))
            scored.append((c, score))

    if not scored:
        return None, 0, []

    scored.sort(key=lambda x: x[1], reverse=True)
    best, best_score = scored[0]
    top_candidates = [f"{name} ({score})" for name, score in scored[:3]]
    return best, int(best_score), top_candidates


def classify_query_intent(message: str) -> dict:
    """Rule-based intent classifier returning intent info and confidence."""
    text = (message or '').lower()
    intent = 'general_rag'
    requires_database = False
    requires_exact_numeric_answer = False
    confidence = 0.5

    # quick helpers
    month_hint = any(m in text for m in MONTH_NAME_LOOKUP) or any(phrase in text for phrase in ['this month', 'last month', 'current month'])
    count_query = any(phrase in text for phrase in ['how many', 'count', 'number of', 'no of', 'total number'])
    wants_list = any(word in text for word in ['list', 'show', 'display']) and 'pending' in text

    # Detect if a client/party name is explicitly mentioned (more specific patterns)
    # Only set to True if we have explicit client keywords followed by a name
    has_client_keyword = any(word in text for word in ['client', 'party', 'customer', 'vendor', ' of '])
    has_payment_history = any(word in text for word in ['payment history', 'payments history', 'payments made'])
    has_for_keyword = ' for ' in text
    has_outstanding = 'outstanding' in text or 'balance' in text
    
    # requires_party_name is True only if:
    # 1. Payment history pattern (always needs party), OR
    # 2. Query has "for [client]" pattern (e.g., "for Enviro Control"), OR
    # 3. Query has "of [client]" pattern but NOT "number of" or "total of", OR  
    # 4. Query has outstanding/balance which implies client
    requires_party_name = (
        has_payment_history or
        has_for_keyword or
        (has_client_keyword and 'number of' not in text and 'total of' not in text) or
        (has_outstanding and 'number' not in text and 'total' not in text)
    )

    # mapping rules
    if has_payment_history:
        intent = 'payment_history'
        requires_database = True
        requires_exact_numeric_answer = False
        requires_party_name = True
        confidence = 0.9
    elif any(word in text for word in ['bank statement', 'statement', 'deposit', 'narration', 'transaction', 'reference']):
        intent = 'statement_query'
        requires_database = True
        requires_exact_numeric_answer = False
        requires_party_name = False
        confidence = 0.85
    elif month_hint and any(word in text for word in ['bill', 'invoice', 'invoices', 'bills']):
        intent = 'month_bill_count'
        requires_database = True
        requires_exact_numeric_answer = True
        requires_party_name = False
        confidence = 0.95
    elif 'pending' in text or any(word in text for word in ['outstanding', 'balance', 'remaining', 'due']):
        requires_database = True
        if count_query:
            intent = 'pending_bill_count'
            requires_exact_numeric_answer = True
            requires_party_name = False
            confidence = 0.95
        elif wants_list or 'pending bills' in text or 'pending invoices' in text:
            intent = 'pending_bill_list'
            requires_exact_numeric_answer = False
            requires_party_name = False
            confidence = 0.9
        else:
            if requires_party_name:
                intent = 'client_pending_amount'
            else:
                intent = 'total_pending_amount'
            requires_exact_numeric_answer = True
            confidence = 0.95
    elif count_query and any(word in text for word in ['bill', 'invoice', 'invoices', 'bills']):
        requires_database = True
        requires_exact_numeric_answer = True
        if requires_party_name:
            intent = 'client_invoice_count'
            confidence = 0.95
        else:
            intent = 'bill_count'
            requires_party_name = False
            confidence = 0.9
    elif any(phrase in text for phrase in ['total billed', 'total invoice amount', 'grand total', 'total amount of invoices']):
        intent = 'total_invoice_amount'
        requires_database = True
        requires_exact_numeric_answer = True
        requires_party_name = False
        confidence = 0.9
    elif any(phrase in text for phrase in ['latest invoice', 'recent bill', 'last invoice']):
        intent = 'latest_invoice'
        requires_database = True
        requires_exact_numeric_answer = False
        requires_party_name = False
        confidence = 0.8
    elif any(word in text for word in ['overdue', 'past due', 'unpaid after']):
        intent = 'overdue_invoice'
        requires_database = True
        requires_exact_numeric_answer = True
        requires_party_name = False
        confidence = 0.9
    else:
        intent = 'general_rag'
        requires_database = False
        requires_exact_numeric_answer = False
        requires_party_name = False
        confidence = 0.6

    # Some intents should support global (fiscal-year or month) queries
    supports_global = intent in ('pending_bill_count', 'month_bill_count', 'bill_count', 'pending_bill_list', 'total_pending_amount', 'total_invoice_amount') or month_hint

    return {
        'intent': intent,
        'requires_database': requires_database,
        'requires_exact_numeric_answer': requires_exact_numeric_answer,
        'requires_party_name': requires_party_name,
        'supports_global_query': bool(supports_global),
        'confidence': float(confidence),
    }


def classify_intent_with_blocks(message: str) -> dict:
    """
    Enhanced intent classifier using structured Intent Blocks with fuzzy matching.
    
    Steps:
    1. Normalize message (fix typos using fuzzy matching)
    2. Try to match against intent block examples
    3. Extract party name and month if needed
    4. Return comprehensive intent info
    """
    try:
        # Step 1: Normalize the message (fix typos)
        normalized_message = normalize_message(message)
        logger.debug(f'Message normalized: "{message}" -> "{normalized_message}"')
        
        # Step 2: Classify intent using intent blocks
        intent_name, confidence = classify_intent(normalized_message)
        
        if intent_name and confidence >= 60:
            # Step 3: Get intent configuration
            intent_config = get_intent_config(intent_name)
            
            # Step 4: Extract party and month if needed
            party_name = None
            month = None
            if intent_config.get('requires_party'):
                party_name = extract_party(message)  # Use original message for extraction
            if intent_config.get('requires_month'):
                month = extract_month(message)
            
            result = {
                'intent': intent_name,
                'requires_database': intent_config.get('requires_db', False),
                'requires_exact_numeric_answer': intent_config.get('requires_db', False),
                'requires_party_name': intent_config.get('requires_party', False),
                'requires_month': intent_config.get('requires_month', False),
                'supports_global_query': True,
                'confidence': float(confidence),
                'source': 'intent_block',
                'handler': intent_config.get('handler'),
                'collection': intent_config.get('collection'),
                'operation': intent_config.get('operation'),
                'extracted_party': party_name,
                'extracted_month': month,
                'normalized_message': normalized_message,
            }
            
            logger.info(f'Intent block classified: intent={intent_name} confidence={confidence} requires_db={intent_config.get("requires_db")} party={party_name} month={month}')
            return result
        
        # Fall back to the general RAG intent instead of the legacy classifier.
        return {
            'intent': 'general_rag',
            'requires_database': False,
            'requires_exact_numeric_answer': False,
            'requires_party_name': False,
            'requires_month': False,
            'supports_global_query': False,
            'confidence': 0.0,
            'source': 'intent_block',
            'handler': 'rag',
            'collection': None,
            'operation': None,
            'extracted_party': None,
            'extracted_month': None,
            'normalized_message': normalized_message,
        }
        
    except Exception as e:
        logger.exception(f'Error in intent block classification: {e}')
        return {
            'intent': 'general_rag',
            'requires_database': False,
            'requires_exact_numeric_answer': False,
            'requires_party_name': False,
            'requires_month': False,
            'supports_global_query': False,
            'confidence': 0.0,
            'source': 'intent_block',
            'handler': 'rag',
            'collection': None,
            'operation': None,
            'extracted_party': None,
            'extracted_month': None,
            'normalized_message': message,
        }


def validate_financial_response(answer: str, source: str, intent_info: dict) -> str | None:
    """Ensure exact numeric intents are only answered from database.
    Returns None if valid, otherwise an error string to return to user."""
    if intent_info.get('requires_exact_numeric_answer') and source != 'database':
        return "I cannot confirm the exact value from the database. Please check the client name, fiscal year, or uploaded data."
    return None


async def _relaxed_party_search(db: AsyncIOMotorDatabase, party_name: str) -> tuple[int, dict]:
    """Perform a broader, non-anchored search for party_name across bills.
    Returns (total_count, {fiscal_year: count, ...})."""
    if not party_name:
        return 0, {}
    # Use a substring (non-anchored) case-insensitive regex to catch near matches
    q = {'party_name': {'$regex': re.escape(party_name), '$options': 'i'}}
    docs = await db['bills'].find(q).to_list(length=5000)
    if not docs:
        return 0, {}
    total = len(docs)
    per_fy: dict = {}
    for d in docs:
        fy = d.get('fiscal_year') or 'unknown'
        per_fy[fy] = per_fy.get(fy, 0) + 1
    return total, per_fy


async def _query_database_answer(db: AsyncIOMotorDatabase, message: str, fiscal_year: str | None) -> dict | None:
    """Answer common questions directly from MongoDB before falling back to RAG."""
    if not _looks_like_structured_query(message):
        return None

    month, year = _parse_month_and_year(message)
    statuses = _normalize_status_filters(message)
    text = (message or '').lower()
    count_query = _is_count_query(message)
    party_name = _extract_party_name(message)

    # Classify intent using Intent Blocks with fuzzy matching
    intent_info = classify_intent_with_blocks(message)
    logger.info('Chat intent classified: intent=%s requires_db=%s requires_party=%s confidence=%s classifier_source=%s', 
                intent_info.get('intent'), intent_info.get('requires_database'), intent_info.get('requires_party_name'), 
                intent_info.get('confidence'), intent_info.get('source'))

    # Handle party-name requirement: only extract/fuzzy-match when intent requires a party
    fuzzy_used = False
    matched_party = None
    matched_score = 0
    if intent_info.get('requires_party_name'):
        # ensure we have an extracted party name
        if not party_name:
            # ask user for a client name instead of proceeding
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name for this query (e.g. "Enviro Control Private LTD").',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }

        best, score, top_candidates = await fuzzy_match_party(db, party_name, fiscal_year)
        if best:
            fuzzy_used = (normalize_party_name(best) != normalize_party_name(party_name))
            matched_party = best
            matched_score = score
            logger.info('Party fuzzy match: extracted=%s matched=%s score=%s', party_name, matched_party, matched_score)
            if score >= 85:
                # Use the matched party name for DB queries
                party_name = matched_party
            elif 65 <= score < 85:
                # Ask clarifying question with top candidates
                return {
                    'status': 'clarify',
                    'response': f'I found multiple close matches for "{party_name}": {", ".join(top_candidates)}. Please confirm which client you mean.',
                    'context_summary': {'extracted': party_name, 'candidates': top_candidates},
                    'tokens_used': 0,
                    'source': 'database',
                }
            else:
                return {
                    'status': 'not_found',
                    'response': 'I could not find this client in the selected fiscal year. Please check the client name or fiscal year.',
                    'context_summary': {'extracted': party_name},
                    'tokens_used': 0,
                    'source': 'database',
                }
    else:
        # Not a client-scoped intent: ignore any extracted party name
        party_name = None

    if month and year is None:
        year = _year_for_month_in_fiscal_year(month, fiscal_year) or datetime.utcnow().year

    include_bills = any(word in text for word in ['bill', 'invoice', 'pending', 'overdue', 'outstanding', 'due', 'total', 'count', 'how many'])
    include_payments = _is_payment_history_query(message) or any(word in text for word in ['payment', 'paid', 'received'])
    include_statements = _is_statement_query(message)

    sections: list[str] = []
    summary: dict = {
        'month': month,
        'year': year,
        'fiscal_year': fiscal_year,
        'party_name': party_name,
    }

    month_filter = bool(month and year)

    # Short-circuit handlers for Intent Block intents
    intent = intent_info.get('intent')
    # Helper base filter
    base_filter = {}
    if fiscal_year:
        base_filter['fiscal_year'] = fiscal_year

    # ============= INTENT BLOCK HANDLERS =============
    
    # GREETING
    if intent == 'greeting':
        return {
            'status': 'success',
            'response': "Hello! I'm here to help with your payment and invoice queries. What would you like to know?",
            'context_summary': {},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # TOTAL RECEIVED AMOUNT (all payments across all fiscal year)
    if intent == 'total_received_amount':
        payments = await db['payments'].find(base_filter).to_list(length=10000)
        total_received = sum(float(p.get('amount') or 0) for p in payments)
        return {
            'status': 'success',
            'response': f'Total payment received till date: {_format_money(total_received)} (source: database)',
            'context_summary': {'total_received': total_received, 'fiscal_year': fiscal_year},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT PENDING AMOUNT
    if intent == 'client_pending_amount':
        extracted_party = intent_info.get('extracted_party')
        if not extracted_party:
            extracted_party = party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name for this query.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        # Fuzzy match party name
        best, score, candidates = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        elif score < 85 and score > 0:
            return {
                'status': 'clarify',
                'response': f'Multiple matches found for "{extracted_party}": {", ".join(candidates)}. Which one?',
                'context_summary': {'extracted': extracted_party, 'candidates': candidates},
                'tokens_used': 0,
                'source': 'database',
            }
        
        query = {'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'}, **base_filter}
        bills = await db['bills'].find(query).to_list(length=5000)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        
        return {
            'status': 'success',
            'response': f'Total pending amount for {extracted_party}: {_format_money(total_pending)} (source: database)',
            'context_summary': {'party_name': extracted_party, 'total_pending': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT BILL COUNT
    if intent == 'client_bill_count':
        extracted_party = intent_info.get('extracted_party') or party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        query = {'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'}, **base_filter}
        count = await db['bills'].count_documents(query)
        
        return {
            'status': 'success',
            'response': f'{extracted_party} has {count} invoice(s) in the selected fiscal year (source: database)',
            'context_summary': {'party_name': extracted_party, 'invoice_count': count},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT TOTAL BILLING
    if intent == 'client_total_billing':
        extracted_party = intent_info.get('extracted_party') or party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        query = {'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'}, **base_filter}
        bills = await db['bills'].find(query).to_list(length=5000)
        total_billing = sum(float(b.get('grand_total') or 0) for b in bills)
        
        return {
            'status': 'success',
            'response': f'Total billing for {extracted_party}: {_format_money(total_billing)} (source: database)',
            'context_summary': {'party_name': extracted_party, 'total_billing': total_billing},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT TOTAL GST
    if intent == 'client_total_gst':
        extracted_party = intent_info.get('extracted_party') or party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        query = {'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'}, **base_filter}
        bills = await db['bills'].find(query).to_list(length=5000)
        gst_values = [_extract_bill_gst_total(b) for b in bills]
        gst_values = [value for value in gst_values if value is not None]
        if not gst_values:
            return {
                'status': 'success',
                'response': f'GST fields are not available in bill records for {extracted_party}. Source: database',
                'context_summary': {'party_name': extracted_party, 'gst_available': False},
                'tokens_used': 0,
                'source': 'database',
            }

        total_gst = sum(gst_values)
        
        return {
            'status': 'success',
            'response': f'Total GST for {extracted_party}: {_format_money(total_gst)} (source: database)',
            'context_summary': {'party_name': extracted_party, 'total_gst': total_gst},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT PENDING BILLS
    if intent == 'client_pending_bills':
        extracted_party = intent_info.get('extracted_party') or party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        query = {
            'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'}, 
            **base_filter,
            '$or': [
                {'status': {'$in': ['PENDING', 'UNPAID', 'PARTIAL']}},
                {'remaining_amount': {'$gt': 0}}
            ]
        }
        bills = await db['bills'].find(query).sort([('invoice_date', -1)]).to_list(length=50)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        
        lines = []
        for b in bills[:10]:
            inv_no = b.get('invoice_no', 'N/A')
            inv_date = b.get('invoice_date')
            if isinstance(inv_date, datetime):
                inv_date = inv_date.strftime('%Y-%m-%d')
            remaining = float(b.get('remaining_amount') or 0)
            lines.append(f"- {inv_no} | {inv_date or 'N/A'} | {_format_money(remaining)}")
        
        resp = f"Pending bills for {extracted_party}:\n" + "\n".join(lines) + f"\n\nTotal Pending: {_format_money(total_pending)}"
        
        return {
            'status': 'success',
            'response': resp,
            'context_summary': {'party_name': extracted_party, 'total_pending': total_pending, 'count': len(bills)},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT MONTH BILL COUNT
    if intent == 'client_month_bill_count':
        extracted_party = intent_info.get('extracted_party') or party_name
        extracted_month = intent_info.get('extracted_month')
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        if not extracted_month:
            extracted_month, _ = _parse_month_and_year(message)
        
        if not extracted_month:
            return {
                'status': 'clarify',
                'response': 'Please specify the month (e.g., "in May").',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        month_year = _year_for_month_in_fiscal_year(extracted_month, fiscal_year) or datetime.utcnow().year
        
        query = {
            'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'},
            'invoice_date': {'$gte': datetime(month_year, extracted_month, 1), '$lt': _next_month_start(month_year, extracted_month)},
            **base_filter
        }
        count = await db['bills'].count_documents(query)
        
        return {
            'status': 'success',
            'response': f'{extracted_party} has {count} invoice(s) in {calendar.month_name[extracted_month]} (source: database)',
            'context_summary': {'party_name': extracted_party, 'month': extracted_month, 'count': count},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT MONTH TOTAL BILLING
    if intent == 'client_month_total_billing':
        extracted_party = intent_info.get('extracted_party') or party_name
        extracted_month = intent_info.get('extracted_month')
        
        if not extracted_party or not extracted_month:
            return {
                'status': 'clarify',
                'response': 'Please specify client name and month.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        month_year = _year_for_month_in_fiscal_year(extracted_month, fiscal_year) or datetime.utcnow().year
        
        query = {
            'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'},
            'invoice_date': {'$gte': datetime(month_year, extracted_month, 1), '$lt': _next_month_start(month_year, extracted_month)},
            **base_filter
        }
        bills = await db['bills'].find(query).to_list(length=5000)
        total_billing = sum(float(b.get('grand_total') or 0) for b in bills)
        
        return {
            'status': 'success',
            'response': f'Total billing for {extracted_party} in {calendar.month_name[extracted_month]}: {_format_money(total_billing)} (source: database)',
            'context_summary': {'party_name': extracted_party, 'month': extracted_month, 'total': total_billing},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT MONTH TOTAL GST
    if intent == 'client_month_total_gst':
        extracted_party = intent_info.get('extracted_party') or party_name
        extracted_month = intent_info.get('extracted_month')
        
        if not extracted_party or not extracted_month:
            return {
                'status': 'clarify',
                'response': 'Please specify client name and month.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        month_year = _year_for_month_in_fiscal_year(extracted_month, fiscal_year) or datetime.utcnow().year
        
        query = {
            'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'},
            'invoice_date': {'$gte': datetime(month_year, extracted_month, 1), '$lt': _next_month_start(month_year, extracted_month)},
            **base_filter
        }
        bills = await db['bills'].find(query).to_list(length=5000)
        gst_values = [_extract_bill_gst_total(b) for b in bills]
        gst_values = [value for value in gst_values if value is not None]
        if not gst_values:
            return {
                'status': 'success',
                'response': f'GST fields are not available in bill records for {extracted_party}. Source: database',
                'context_summary': {'party_name': extracted_party, 'month': extracted_month, 'gst_available': False},
                'tokens_used': 0,
                'source': 'database',
            }

        total_gst = sum(gst_values)
        
        return {
            'status': 'success',
            'response': f'Total GST for {extracted_party} in {calendar.month_name[extracted_month]}: {_format_money(total_gst)} (source: database)',
            'context_summary': {'party_name': extracted_party, 'month': extracted_month, 'total_gst': total_gst},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT MONTH PENDING BILLS
    if intent == 'client_month_pending_bills':
        extracted_party = intent_info.get('extracted_party') or party_name
        extracted_month = intent_info.get('extracted_month')
        
        if not extracted_party or not extracted_month:
            return {
                'status': 'clarify',
                'response': 'Please specify client name and month.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        best, score, _ = await fuzzy_match_party(db, extracted_party, fiscal_year)
        if best and score >= 85:
            extracted_party = best
        
        month_year = _year_for_month_in_fiscal_year(extracted_month, fiscal_year) or datetime.utcnow().year
        
        query = {
            'party_name': {'$regex': f'^{re.escape(extracted_party)}$', '$options': 'i'},
            'invoice_date': {'$gte': datetime(month_year, extracted_month, 1), '$lt': _next_month_start(month_year, extracted_month)},
            **base_filter,
            '$or': [
                {'status': {'$in': ['PENDING', 'UNPAID', 'PARTIAL']}},
                {'remaining_amount': {'$gt': 0}}
            ]
        }
        bills = await db['bills'].find(query).sort([('invoice_date', -1)]).to_list(length=50)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        
        lines = []
        for b in bills[:10]:
            inv_no = b.get('invoice_no', 'N/A')
            remaining = float(b.get('remaining_amount') or 0)
            lines.append(f"- {inv_no} | {_format_money(remaining)}")
        
        resp = f"Pending bills for {extracted_party} in {calendar.month_name[extracted_month]}:\n" + "\n".join(lines) + f"\n\nTotal Pending: {_format_money(total_pending)}"
        
        return {
            'status': 'success',
            'response': resp,
            'context_summary': {'party_name': extracted_party, 'month': extracted_month, 'total': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }
    
    # CLIENT STATEMENT ENTRY COUNT
    if intent == 'client_statement_entry_count':
        extracted_party = intent_info.get('extracted_party') or party_name
        
        if not extracted_party:
            return {
                'status': 'clarify',
                'response': 'Please specify the client/party name.',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        
        query = {
            '$or': [
                {'narration': {'$regex': extracted_party, '$options': 'i'}},
                {'reference': {'$regex': extracted_party, '$options': 'i'}}
            ],
            **base_filter
        }
        count = await db['statement_entries'].count_documents(query)
        
        return {
            'status': 'success',
            'response': f'Found {count} statement entries for {extracted_party} (source: database)',
            'context_summary': {'party_name': extracted_party, 'count': count},
            'tokens_used': 0,
            'source': 'database',
        }

    # ============= END INTENT BLOCK HANDLERS =============

    if intent == 'global_total_pending_amount':
        pend_filter = build_pending_filter(base_filter)
        docs = await db['bills'].find(pend_filter).to_list(length=5000)
        total_pending = sum(float(d.get('remaining_amount') or 0) for d in docs)
        return {
            'status': 'success',
            'response': f'Total pending amount in the selected fiscal year is {_format_money(total_pending)}. Source: database',
            'context_summary': {'fiscal_year': fiscal_year, 'total_pending': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'global_pending_bill_count':
        pend_filter = build_pending_filter(base_filter)
        bills_count = await db['bills'].count_documents(pend_filter)
        return {
            'status': 'success',
            'response': f'There are {bills_count} pending bill(s) in the selected fiscal year. Source: database',
            'context_summary': {'fiscal_year': fiscal_year, 'pending_bill_count': bills_count},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'global_pending_bills_list':
        pend_filter = build_pending_filter(base_filter)
        total_count = await db['bills'].count_documents(pend_filter)
        bills = await db['bills'].find(pend_filter).sort([('invoice_date', -1)]).to_list(length=10)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        lines = []
        for idx, bill in enumerate(bills, start=1):
            inv_date = bill.get('invoice_date')
            if isinstance(inv_date, datetime):
                inv_date = inv_date.strftime('%Y-%m-%d')
            lines.append(
                f"{idx}. Invoice {bill.get('invoice_no') or 'N/A'} | Party: {bill.get('party_name') or 'N/A'} | Date: {inv_date or 'N/A'} | Remaining: {_format_money(bill.get('remaining_amount'))}"
            )
        response = (
            f'I found {total_count} pending bill(s). Total pending amount: {_format_money(total_pending)}.\n'
            f'Showing first {len(bills)} of {total_count} pending bills:\n' + '\n'.join(lines) + '\nSource: database'
        )
        return {
            'status': 'success',
            'response': response,
            'context_summary': {'fiscal_year': fiscal_year, 'total_count': total_count, 'shown': len(bills), 'total_pending': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'global_month_bill_count':
        if not month_filter:
            return {
                'status': 'clarify',
                'response': 'Please specify the month (for example, "in December").',
                'context_summary': {},
                'tokens_used': 0,
                'source': 'database',
            }
        bill_query = dict(base_filter)
        bill_query['invoice_date'] = {'$gte': datetime(year, month, 1), '$lt': _next_month_start(year, month)}
        bills_count = await db['bills'].count_documents(bill_query)
        return {
            'status': 'success',
            'response': f'There are {bills_count} bill(s) in {calendar.month_name[month]} {year}. Source: database',
            'context_summary': {'fiscal_year': fiscal_year, 'month': month, 'year': year, 'bill_count': bills_count},
            'tokens_used': 0,
            'source': 'database',
        }

    # month-based counts
    if intent == 'month_bill_count' or (intent == 'invoice_count' and month_filter and not intent_info.get('requires_party_name')):
        if not month_filter:
            return None
        bill_query = dict(base_filter)
        bill_query['invoice_date'] = {'$gte': datetime(year, month, 1), '$lt': _next_month_start(year, month)}
        bills_count = await db['bills'].count_documents(bill_query)
        return {
            'status': 'success',
            'response': f'There are {bills_count} bill(s) in {calendar.month_name[month]} for the selected fiscal year. (source: database)',
            'context_summary': {'month': month, 'year': year, 'fiscal_year': fiscal_year},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'pending_bill_count':
        pend_filter = build_pending_filter(base_filter)
        bills_count = await db['bills'].count_documents(pend_filter)
        return {
            'status': 'success',
            'response': f'There are {bills_count} pending bill(s) in the selected fiscal year. (source: database)',
            'context_summary': {'fiscal_year': fiscal_year},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'pending_bill_list':
        pend_filter = build_pending_filter(base_filter)
        total_count = await db['bills'].count_documents(pend_filter)
        bills = await db['bills'].find(pend_filter).sort([('invoice_date', -1)]).to_list(length=10)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        lines = []
        for b in bills:
            inv_date = b.get('invoice_date')
            if isinstance(inv_date, datetime):
                inv_date = inv_date.strftime('%Y-%m-%d')
            lines.append(f"- {b.get('invoice_no','N/A')} | {b.get('party_name','N/A')} | {inv_date or 'N/A'} | {_format_money(b.get('remaining_amount'))}")
        resp = f"Showing first {len(bills)} of {total_count} pending bills.\nTotal pending (first {len(bills)} shown): {_format_money(total_pending)}\n\n" + "\n".join(lines)
        return {
            'status': 'success',
            'response': resp,
            'context_summary': {'count_shown': len(bills), 'total_count': total_count},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'total_pending_amount':
        pend_filter = build_pending_filter(base_filter)
        docs = await db['bills'].find(pend_filter).to_list(length=5000)
        total_pending = sum(float(d.get('remaining_amount') or 0) for d in docs)
        return {
            'status': 'success',
            'response': f'Total pending amount for the selected fiscal year is {_format_money(total_pending)}. (source: database)',
            'context_summary': {'fiscal_year': fiscal_year, 'total_pending': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }

    # client-scoped intents
    if intent == 'client_pending_amount' and party_name:
        bill_query = dict(base_filter)
        bill_query['party_name'] = {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}
        pend_filter = build_pending_filter(bill_query)
        docs = await db['bills'].find(pend_filter).to_list(length=5000)
        total_pending = sum(float(d.get('remaining_amount') or 0) for d in docs)
        return {
            'status': 'success',
            'response': f'Your total pending amount for {party_name} in the selected fiscal year is {_format_money(total_pending)}. (source: database)',
            'context_summary': {'party_name': party_name, 'total_pending': total_pending},
            'tokens_used': 0,
            'source': 'database',
        }

    if intent == 'client_invoice_count' and party_name:
        bill_query = dict(base_filter)
        bill_query['party_name'] = {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}
        bills_count = await db['bills'].count_documents(bill_query)
        return {
            'status': 'success',
            'response': f'You have {bills_count} invoice(s) for {party_name} in the selected fiscal year. (source: database)',
            'context_summary': {'party_name': party_name, 'bills_count': bills_count},
            'tokens_used': 0,
            'source': 'database',
        }

    if include_bills and party_name and (_is_invoice_count_query(message) or _is_pending_amount_query(message) or _is_total_billed_amount_query(message)):
        bill_query: dict = {}
        if fiscal_year:
            bill_query['fiscal_year'] = fiscal_year
        bill_query['party_name'] = {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}
        if month_filter:
            bill_query['invoice_date'] = {
                '$gte': datetime(year, month, 1),
                '$lt': _next_month_start(year, month),
            }

        if _is_invoice_count_query(message):
            bills_count = await db['bills'].count_documents(bill_query)
            if bills_count == 0:
                # Relaxed fallback: search across all fiscal years with a non-anchored party match
                total_relaxed, per_fy = await _relaxed_party_search(db, party_name)
                if total_relaxed > 0:
                    # Build a short per-fiscal-year summary
                    per_fy_items = [f"{fy}: {cnt}" for fy, cnt in per_fy.items()]
                    per_fy_text = ", ".join(per_fy_items)
                    return {
                        'status': 'success',
                        'response': f'You have 0 invoice(s) for {party_name} in the selected fiscal year. However, I found {total_relaxed} invoice(s) for this client across other fiscal years: {per_fy_text}.',
                        'context_summary': summary,
                        'tokens_used': 0,
                        'source': 'database',
                    }
            summary['bills_count'] = bills_count
            if month_filter:
                return {
                    'status': 'success',
                    'response': f'You have {bills_count} invoice(s) for {party_name} in {calendar.month_name[month]} {year}.',
                    'context_summary': summary,
                    'tokens_used': 0,
                    'source': 'database',
                }
            return {
                'status': 'success',
                'response': f'You have {bills_count} invoice(s) for {party_name} in the selected fiscal year.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        bills = await db['bills'].find(bill_query).to_list(length=1000)
        total_grand = sum(float(b.get('grand_total') or 0) for b in bills)
        total_pending = sum(float(b.get('remaining_amount') or 0) for b in bills)
        summary['bills_count'] = len(bills)
        summary['total_grand'] = total_grand
        summary['total_pending'] = total_pending

        if _is_pending_amount_query(message):
            label = f' in {calendar.month_name[month]} {year}' if month_filter else ' in the selected fiscal year'
            return {
                'status': 'success',
                'response': f'Your total pending amount for {party_name}{label} is {_format_money(total_pending)}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        if _is_total_billed_amount_query(message):
            label = f' in {calendar.month_name[month]} {year}' if month_filter else ' in the selected fiscal year'
            return {
                'status': 'success',
                'response': f'Your total billed amount for {party_name}{label} is {_format_money(total_grand)}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

    if include_bills and party_name and not month_filter:
        bill_query = {'party_name': {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}}
        if fiscal_year:
            bill_query['fiscal_year'] = fiscal_year
        bills = await db['bills'].find(bill_query).to_list(length=1000)
        bills_count = len(bills)
        if bills_count == 0:
            total_relaxed, per_fy = await _relaxed_party_search(db, party_name)
            if total_relaxed > 0:
                per_fy_items = [f"{fy}: {cnt}" for fy, cnt in per_fy.items()]
                per_fy_text = ", ".join(per_fy_items)
                return {
                    'status': 'success',
                    'response': f'No invoices found for {party_name} in the selected fiscal year. However I found {total_relaxed} invoice(s) across other fiscal years: {per_fy_text}.',
                    'context_summary': summary,
                    'tokens_used': 0,
                    'source': 'database',
                }
        total_amount = sum(float(b.get('grand_total') or 0) for b in bills)
        summary['bills_count'] = bills_count
        summary['total_grand'] = total_amount

        if count_query:
            return {
                'status': 'success',
                'response': f'You have {bills_count} invoice(s) for {party_name} in the selected fiscal year.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        if _is_pending_amount_query(message):
            total_pending = sum(float(b.get('remaining_amount') or b.get('grand_total') or 0) for b in bills if str(b.get('status') or '').upper() in PENDING_STATUS_SET)
            summary['total_pending'] = total_pending
            return {
                'status': 'success',
                'response': f'Your total pending amount for {party_name} in the selected fiscal year is {_format_money(total_pending)}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        if _is_total_billed_amount_query(message):
            return {
                'status': 'success',
                'response': f'Your total billed amount for {party_name} in the selected fiscal year is {_format_money(total_amount)}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

    if include_payments and party_name:
        payment_query: dict = {'party_name': {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}}
        if fiscal_year:
            payment_query['fiscal_year'] = fiscal_year
        if month_filter:
            payment_query['payment_date'] = {
                '$gte': datetime(year, month, 1),
                '$lt': _next_month_start(year, month),
            }

        payments = await db['payments'].find(payment_query).sort([('payment_date', 1), ('payment_id', 1)]).to_list(length=200)
        total_payments = sum(float(p.get('amount') or 0) for p in payments)
        summary['payments_count'] = len(payments)
        summary['total_payments'] = total_payments

        if _is_payment_history_query(message) or count_query:
            if month_filter:
                return {
                    'status': 'success',
                    'response': f'You have {len(payments)} payment record(s) for {party_name} in {calendar.month_name[month]} {year}. Total received: {_format_money(total_payments)}.',
                    'context_summary': summary,
                    'tokens_used': 0,
                    'source': 'database',
                }
            return {
                'status': 'success',
                'response': f'You have {len(payments)} payment record(s) for {party_name} in the selected fiscal year. Total received: {_format_money(total_payments)}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        if payments:
            lines = []
            for payment in payments[:12]:
                pay_date = payment.get('payment_date')
                if isinstance(pay_date, datetime):
                    pay_date = pay_date.strftime('%Y-%m-%d')
                lines.append(
                    f"- Payment {payment.get('payment_id', 'N/A')} | Date: {pay_date or 'N/A'} | Amount: {_format_money(payment.get('amount'))} | Reference: {payment.get('reference') or 'N/A'}"
                )
            return {
                'status': 'success',
                'response': f'Found {len(payments)} payment(s) for {party_name}. Total received: {_format_money(total_payments)}.\n\nPayments:\n' + '\n'.join(lines),
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

    if include_statements and month_filter:
        statement_query: dict = {}
        if fiscal_year:
            statement_query['fiscal_year'] = fiscal_year
        statement_query['value_date'] = {
            '$gte': datetime(year, month, 1),
            '$lt': _next_month_start(year, month),
        }

        statements = await db['statement_entries'].find(statement_query).to_list(length=1000)
        total_deposits = sum(float(s.get('deposit') or 0) for s in statements)
        summary['statements_count'] = len(statements)
        summary['total_deposits'] = total_deposits

        if _is_count_query(message):
            return {
                'status': 'success',
                'response': f'You have {len(statements)} statement entry/entries in {calendar.month_name[month]} {year}.',
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        return {
            'status': 'success',
            'response': f'I found {len(statements)} statement entry/entries in {calendar.month_name[month]} {year}. Total deposits: {_format_money(total_deposits)}.',
            'context_summary': summary,
            'tokens_used': 0,
            'source': 'database',
        }

    if include_bills:
        bill_query: dict = {}
        if fiscal_year:
            bill_query['fiscal_year'] = fiscal_year
        if party_name:
            bill_query['party_name'] = {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'}
        if month and year:
            bill_query['invoice_date'] = {
                '$gte': datetime(year, month, 1),
                '$lt': _next_month_start(year, month),
            }
        if statuses:
            bill_query['status'] = {'$in': list(statuses)}

        bills_count = await db['bills'].count_documents(bill_query)
        summary['bills_count'] = bills_count
        if bills_count == 0 and party_name:
            total_relaxed, per_fy = await _relaxed_party_search(db, party_name)
            if total_relaxed > 0:
                per_fy_items = [f"{fy}: {cnt}" for fy, cnt in per_fy.items()]
                per_fy_text = ", ".join(per_fy_items)
                return {
                    'status': 'success',
                    'response': f'No invoices found for {party_name} in the selected fiscal year. However I found {total_relaxed} invoice(s) across other fiscal years: {per_fy_text}.',
                    'context_summary': summary,
                    'tokens_used': 0,
                    'source': 'database',
                }
        if count_query:
            if month and year:
                party_fragment = f" for {party_name}" if party_name else ""
                if statuses and statuses <= PENDING_STATUS_SET:
                    sections.append(
                        f"You have {bills_count} pending bill(s){party_fragment} in {calendar.month_name[month]} {year}."
                    )
                elif statuses == PAID_STATUS_SET:
                    sections.append(
                        f"You have {bills_count} paid bill(s){party_fragment} in {calendar.month_name[month]} {year}."
                    )
                else:
                    sections.append(
                        f"You have {bills_count} bill(s){party_fragment} in {calendar.month_name[month]} {year}."
                    )
            else:
                if party_name:
                    sections.append(f"You have {bills_count} invoice(s) for {party_name} in the selected fiscal year.")
                else:
                    sections.append(f"You have {bills_count} bill(s) in the selected fiscal year.")

            return {
                'status': 'success',
                'response': ' '.join(sections),
                'context_summary': summary,
                'tokens_used': 0,
                'source': 'database',
            }

        bills = await db['bills'].find(bill_query).sort([('invoice_date', 1), ('invoice_no', 1)]).to_list(length=200)

        if bills:
            total_pending = sum(float(b.get('remaining_amount') or b.get('grand_total') or 0) for b in bills)
            total_grand = sum(float(b.get('grand_total') or 0) for b in bills)
            lines = []
            for bill in bills[:12]:
                inv_date = bill.get('invoice_date')
                if isinstance(inv_date, datetime):
                    inv_date = inv_date.strftime('%Y-%m-%d')
                lines.append(
                    f"- Bill {bill.get('invoice_no', 'N/A')} | Party: {bill.get('party_name', 'N/A')} | "
                    f"Date: {inv_date or 'N/A'} | Status: {bill.get('status', 'N/A')} | "
                    f"Amount: {_format_money(bill.get('grand_total'))} | Remaining: {_format_money(bill.get('remaining_amount'))}"
                )

            if statuses and statuses <= PENDING_STATUS_SET:
                sections.append(
                    f"I found {len(bills)} pending bill(s) for {calendar.month_name[month] if month else 'the selected period'} {year or ''}. "
                    f"Total pending amount: {_format_money(total_pending)}."
                )
            elif statuses == PAID_STATUS_SET:
                sections.append(
                    f"I found {len(bills)} paid bill(s) for {calendar.month_name[month] if month else 'the selected period'} {year or ''}. "
                    f"Total billed amount: {_format_money(total_grand)}."
                )
            else:
                sections.append(
                    f"I found {len(bills)} bill(s) for {calendar.month_name[month] if month else 'the selected period'} {year or ''}. "
                    f"Total billed amount: {_format_money(total_grand)}."
                )
            sections.append("Bills:\n" + "\n".join(lines))
        else:
            sections.append("No matching bills were found in the bills collection for that query.")

    if include_payments:
        payment_query: dict = {}
        if fiscal_year:
            payment_query['fiscal_year'] = fiscal_year
        if month and year:
            payment_query['payment_date'] = {
                '$gte': datetime(year, month, 1),
                '$lt': _next_month_start(year, month),
            }

        payments = await db['payments'].find(payment_query).sort([('payment_date', 1), ('payment_id', 1)]).to_list(length=200)
        summary['payments_count'] = len(payments)
        if payments:
            total_payments = sum(float(p.get('amount') or 0) for p in payments)
            lines = []
            for payment in payments[:12]:
                pay_date = payment.get('payment_date')
                if isinstance(pay_date, datetime):
                    pay_date = pay_date.strftime('%Y-%m-%d')
                lines.append(
                    f"- Payment {payment.get('payment_id', 'N/A')} | Party: {payment.get('party_name', 'N/A')} | "
                    f"Date: {pay_date or 'N/A'} | Amount: {_format_money(payment.get('amount'))} | Reference: {payment.get('reference') or 'N/A'}"
                )
            sections.append(
                f"I found {len(payments)} payment(s) in the payments collection. Total received: {_format_money(total_payments)}."
            )
            sections.append("Payments:\n" + "\n".join(lines))
        else:
            sections.append("No matching payments were found in the payments collection for that query.")

    if include_statements:
        statement_query: dict = {}
        if fiscal_year:
            statement_query['fiscal_year'] = fiscal_year
        if month and year:
            statement_query['value_date'] = {
                '$gte': datetime(year, month, 1),
                '$lt': _next_month_start(year, month),
            }

        statements = await db['statement_entries'].find(statement_query).sort([('value_date', 1)]).to_list(length=200)
        summary['statements_count'] = len(statements)
        if statements:
            total_deposits = sum(float(s.get('deposit') or 0) for s in statements)
            lines = []
            for entry in statements[:12]:
                value_date = entry.get('value_date_display') or entry.get('value_date')
                if isinstance(value_date, datetime):
                    value_date = value_date.strftime('%Y-%m-%d')
                lines.append(
                    f"- {value_date or 'N/A'} | {entry.get('narration') or 'N/A'} | Ref: {entry.get('reference') or 'N/A'} | Deposit: {_format_money(entry.get('deposit'))}"
                )
            sections.append(
                f"I found {len(statements)} statement entry/entries. Total deposits: {_format_money(total_deposits)}."
            )
            sections.append("Statements:\n" + "\n".join(lines))
        else:
            sections.append("No matching statement entries were found for that query.")

    if not sections:
        return None

    answer = "\n\n".join(sections)
    return {
        'status': 'success',
        'response': answer,
        'context_summary': summary,
        'tokens_used': 0,
        'source': 'database',
    }

# Endpoints

@router.post("/train", response_model=TrainResponse)
async def train_index(
    request: Request,
    train_req: TrainRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Train the RAG index for a fiscal year across bills, payments, and statements."""
    try:
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")

        result = await rag_service.train_fiscal_year(db, train_req.fiscal_year)
        return TrainResponse(
            status=result.get('status', 'success'),
            fiscal_year=result.get('fiscal_year', train_req.fiscal_year),
            indexed=result.get('indexed', {"bills": 0, "payments": 0, "statements": 0, "total": 0}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Training index failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index-status", response_model=IndexStatusResponse)
async def index_status(
    request: Request,
    fiscal_year: Optional[str] = Query(None),
):
    """Return FAISS index status and breakdowns."""
    try:
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")

        summary = vector_store.get_index_summary(fiscal_year=fiscal_year)
        return IndexStatusResponse(
            status='success',
            fiscal_year=fiscal_year,
            total_indexed_documents=summary.get('total_indexed_documents', 0),
            document_type_breakdown=summary.get('document_type_breakdown', {}),
            fiscal_year_breakdown=summary.get('fiscal_year_breakdown', {}),
            sample_metadata=vector_store.get_sample_metadata(limit=3, fiscal_year=fiscal_year),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Index status retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=IndexResponse)
async def index_data(
    request: Request,
    index_req: IndexRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Index bills and payments for the RAG pipeline
    Called when entering a fiscal year or manually to update data
    
    Fiscal year must exist in the fiscal_years collection
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Try both FY storage styles: current code uses `value`, some older docs used `name`.
        fy_doc = await db.fiscal_years.find_one({
            "$or": [
                {"value": index_req.fiscal_year},
                {"name": index_req.fiscal_year},
                {"label": index_req.fiscal_year},
            ]
        })
        
        # Fetch bills for this fiscal year
        bills = await db.bills.find({
            "$or": [
                {"fiscal_year": index_req.fiscal_year},
                {"invoice_date": {
                    "$gte": datetime.strptime(index_req.fiscal_year.replace('FY-', '').split('-')[0] + '-04-01', '%Y-%m-%d'),
                    "$lt": datetime.strptime(index_req.fiscal_year.replace('FY-', '').split('-')[1] + '-04-01', '%Y-%m-%d'),
                }},
            ]
        }).to_list(length=1000)  # Limit to 1000 bills
        
        if not bills:
            return IndexResponse(
                status="warning",
                count=0,
                message=f"No bills found for fiscal year '{index_req.fiscal_year}'"
            )
        
        # Index the data
        result = await rag_service.index_bills_and_payments(bills, index_req.fiscal_year)
        
        return IndexResponse(
            status=result.get('status', 'success'),
            count=result.get('count', 0),
            message=f"Successfully indexed {result.get('count', 0)} bills for fiscal year '{index_req.fiscal_year}'"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_req: ChatRequest,
    include_context: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Send a message to the chatbot
    Uses RAG to retrieve relevant bills and generate response
    
    Query Parameters:
    - include_context: If true, include context summary in response
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get user's current fiscal year
        fiscal_year = getattr(request.state, 'fiscal_year', 'FY-2025-2026')
        
        if not chat_req.message or len(chat_req.message.strip()) == 0:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if len(chat_req.message) > 1000:
            raise HTTPException(status_code=400, detail="Message too long (max 1000 chars)")
        
        # Classify intent using Intent Blocks with fuzzy matching for typos
        intent_info = classify_intent_with_blocks(chat_req.message)
        logger.info({
            'message': chat_req.message,
            'fiscal_year': fiscal_year,
            'intent_info': intent_info,
            'requires_party': intent_info.get('requires_party_name'),
            'route_used': 'database' if intent_info.get('requires_database') else 'rag',
            'handler': intent_info.get('handler'),
        })

        if intent_info.get('intent') == 'greeting':
            greeting_response = "Hello! I'm your payment assistant. Ask me about bills, payments, pending amounts, GST, or any fiscal-year query."
            return ChatResponse(
                response=greeting_response,
                context_summary={} if include_context else None,
                tokens_used=0,
            )

        if intent_info.get('requires_database'):
            # Database-only path for exact financial queries
            direct_answer = await _query_database_answer(db, chat_req.message, fiscal_year)
            if direct_answer:
                if include_context and 'context_summary' not in direct_answer:
                    direct_answer['context_summary'] = {}
                # Logging details
                context_summary = direct_answer.get('context_summary') or {}
                logger.info({
                    'message': chat_req.message,
                    'fiscal_year': fiscal_year,
                    'intent_info': intent_info,
                    'requires_party': intent_info.get('requires_party_name'),
                    'route_used': 'database',
                    'handler': intent_info.get('handler'),
                    'final_source': direct_answer.get('source'),
                    'context_summary': context_summary,
                })
                return ChatResponse(
                    response=direct_answer['response'],
                    context_summary=direct_answer.get('context_summary') if include_context else None,
                    tokens_used=direct_answer.get('tokens_used')
                )

            # Do not fall back to RAG for strict numeric database intents
            logger.info('Database intent but no DB answer found; returning clarification/error (intent=%s)', intent_info.get('intent'))
            if intent_info.get('requires_party_name'):
                return ChatResponse(
                    response='I could not find this client in the selected fiscal year. Please check the client name or fiscal year. Source: database.',
                    context_summary=None,
                    tokens_used=0
                )
            else:
                return ChatResponse(
                    response='I could not find matching records in the selected fiscal year. Source: database.',
                    context_summary=None,
                    tokens_used=0
                )

        # Non-database intents -> use RAG
        result = await rag_service.chat(
            user_message=chat_req.message,
            fiscal_year=fiscal_year,
            top_k=5
        )

        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))

        # Validation: do not accept LLM numbers for exact financial intents
        validation_err = validate_financial_response(result.get('response', ''), result.get('source', 'rag'), intent_info)
        if validation_err:
            logger.warning('Validation blocked LLM answer for intent=%s', intent_info.get('intent'))
            return ChatResponse(response=validation_err, context_summary=None, tokens_used=0)

        # Log RAG usage
        ctx_sum = result.get('context_summary') or {}
        logger.info({
            'message': chat_req.message,
            'fiscal_year': fiscal_year,
            'intent_info': intent_info,
            'requires_party': intent_info.get('requires_party_name'),
            'route_used': 'rag',
            'handler': intent_info.get('handler'),
            'final_source': result.get('source', 'retrieved documents'),
            'context_summary': ctx_sum,
        })

        response = ChatResponse(
            response=result.get('response', ''),
            context_summary=result.get('context_summary') if include_context else None,
            tokens_used=result.get('tokens_used')
        )

        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/history", response_model=HistoryResponse)
async def get_history(request: Request):
    """
    Get conversation history for current session
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        history = rag_service.get_history()
        return HistoryResponse(messages=history)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history/clear")
async def clear_history(request: Request):
    """
    Clear conversation history
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        rag_service.clear_history()
        return {"status": "success", "message": "Conversation history cleared"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status(request: Request):
    """
    Get RAG pipeline status and statistics
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        stats = {
            "vector_store": {
                "indexed_documents": 0,
                "embedding_dimension": 384,
                "model": "all-MiniLM-L6-v2"
            },
            "llm": {
                "model": settings.LLM_MODEL,
                "temperature": 0.7,
                "max_tokens": 500,
                "provider": settings.LLM_PROVIDER
            },
            "history": {
                "messages": len(rag_service.get_history())
            }
        }
        
        return {
            "status": "operational",
            "stats": stats,
            "message": "RAG chatbot is ready"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/test")
async def llm_test(request: Request):
    """
    Test LLM connectivity using configured provider and model.
    Returns a small reply from the model or an error string.
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Use model configured in settings
        model = settings.LLM_MODEL
        # Simple ping message
        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Say hello and confirm model availability."}
        ]

        # Get LLM client and make call
        client = get_llm_client()
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=32, temperature=0.2)
        text = resp.choices[0].message.content
        return {"status": "ok", "provider": settings.LLM_PROVIDER, "model": model, "response": text}

    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/llm/test/public")
async def llm_test_public():
    """
    Public test endpoint for local debugging only (requires DEBUG=True).
    Calls the configured provider/model and returns the response or error.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Public LLM test is only allowed in DEBUG mode")

    model = settings.LLM_MODEL
    messages = [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Respond with 'ok' and include the model name."}
    ]

    try:
        client = get_llm_client()
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=24, temperature=0.0)
        text = resp.choices[0].message.content
        return {"status": "ok", "provider": settings.LLM_PROVIDER, "model": model, "response": text}
    except Exception as e:
        logger.exception("Public LLM test failed")
        return {"status": "error", "error": str(e)}

@router.post("/rebuild-index")
async def rebuild_index(
    request: Request,
    fiscal_year: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Rebuild the entire vector index from scratch
    Useful for updating after bulk bill imports
    Admin only
    """
    try:
        # Check authentication
        if not hasattr(request.state, 'user') or not request.state.user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Only admins can rebuild index
        if getattr(request.state, 'role', 'user') != 'admin':
            raise HTTPException(status_code=403, detail="Only admins can rebuild index")
        
        # Clear existing index
        from app.services.vector_store_service import vector_store
        vector_store.delete_all()
        
        # Reindex
        bills = await db.bills.find({
            "fiscal_year": fiscal_year
        }).to_list(length=1000)
        
        if not bills:
            return IndexResponse(
                status="warning",
                count=0,
                message=f"No bills found for fiscal year '{fiscal_year}'"
            )
        
        result = await rag_service.index_bills_and_payments(bills, fiscal_year)
        
        return IndexResponse(
            status=result.get('status', 'success'),
            count=result.get('count', 0),
            message=f"Successfully rebuilt index with {result.get('count', 0)} bills for fiscal year '{fiscal_year}'"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
