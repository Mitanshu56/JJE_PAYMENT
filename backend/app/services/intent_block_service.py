"""
Intent Block Service - Structured query classification with fuzzy matching for typos
Handles intent detection, synonym resolution, and fuzzy matching
"""

from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = None
    process = None

# Intent Block Definition - Core structure for query understanding
INTENT_BLOCK = {
    "greeting": {
        "examples": [
            "hi", "hello", "hellow", "hey", "how are you"
        ],
        "requires_db": False,
        "requires_party": False,
        "handler": "handle_greeting"
    },

    "total_received_amount": {
        "examples": [
            "tell me total receive amount till date",
            "total recive amount",
            "total received amount",
            "total amount received",
            "received amount till date",
            "collection amount",
            "payment received till date"
        ],
        "requires_db": True,
        "requires_party": False,
        "collection": "payments",
        "operation": "sum amount",
        "handler": "handle_total_received_amount"
    },

    "global_total_pending_amount": {
        "patterns": [
            "total pending amount",
            "total due amount",
            "total overdue amount",
            "total remaining amount",
            "total balance amount",
            "pending amount till date",
            "overall pending amount"
        ],
        "requires_db": True,
        "requires_party": False,
        "collection": "bills",
        "operation": "sum remaining_amount",
        "handler": "handle_global_total_pending_amount"
    },

    "global_pending_bill_count": {
        "patterns": [
            "total pending bills",
            "total number of pending bills",
            "pending bill count",
            "how many pending bills",
            "how many unpaid bills",
            "count pending bills"
        ],
        "requires_db": True,
        "requires_party": False,
        "collection": "bills",
        "operation": "count pending bills",
        "handler": "handle_global_pending_bill_count"
    },

    "global_pending_bills_list": {
        "patterns": [
            "pending bills",
            "show pending bills",
            "show all pending bills",
            "due bills",
            "overdue bills",
            "unpaid bills"
        ],
        "requires_db": True,
        "requires_party": False,
        "collection": "bills",
        "operation": "list pending bills",
        "handler": "handle_global_pending_bills_list"
    },

    "global_month_bill_count": {
        "patterns": [
            "how many bills are there in <month>",
            "bills in <month>",
            "invoice count in <month>",
            "total bills in <month>"
        ],
        "requires_db": True,
        "requires_party": False,
        "requires_month": True,
        "collection": "bills",
        "operation": "count bills by month",
        "handler": "handle_global_month_bill_count"
    },

    "client_pending_amount": {
        "examples": [
            "total pending amount of <party>",
            "pending amount of <party>",
            "due amount of <party>",
            "overdue amount of <party>",
            "remaining amount of <party>",
            "balance amount of <party>"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "bills",
        "operation": "sum remaining_amount",
        "handler": "handle_client_pending_amount"
    },

    "client_bill_count": {
        "examples": [
            "total number of bill of <party>",
            "count no of bill <party>",
            "number of bills of <party>",
            "total bills of <party>",
            "no of invoices of <party>"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "bills",
        "operation": "count bills",
        "handler": "handle_client_bill_count"
    },

    "client_month_bill_count": {
        "examples": [
            "total number of bill of <party> in <month>",
            "count bills of <party> in <month>",
            "number of invoices of <party> in <month>",
            "total bills of <party> in december"
        ],
        "requires_db": True,
        "requires_party": True,
        "requires_month": True,
        "collection": "bills",
        "operation": "count bills by month",
        "handler": "handle_client_month_bill_count"
    },

    "client_total_billing": {
        "examples": [
            "total billing of <party> till date",
            "total bill amount of <party>",
            "total invoice amount of <party>",
            "total amount of bills of <party>",
            "billing amount of <party>"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "bills",
        "operation": "sum grand_total",
        "handler": "handle_client_total_billing"
    },

    "client_month_total_billing": {
        "examples": [
            "total billing of <party> in <month>",
            "total invoice amount of <party> in <month>",
            "total bill amount of <party> in december",
            "billing of <party> in may"
        ],
        "requires_db": True,
        "requires_party": True,
        "requires_month": True,
        "collection": "bills",
        "operation": "sum grand_total by month",
        "handler": "handle_client_month_total_billing"
    },

    "client_statement_entry_count": {
        "examples": [
            "total entry of <party> in my statement",
            "statement entry of <party>",
            "count statement entries of <party>",
            "how many entries of <party> in bank statement"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "statement_entries",
        "operation": "count matching narration/reference/party",
        "handler": "handle_client_statement_entry_count"
    },

    "client_total_gst": {
        "examples": [
            "count total gst of <party>",
            "total gst of <party>",
            "gst amount of <party>",
            "total tax of <party>"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "bills",
        "operation": "sum gst fields",
        "handler": "handle_client_total_gst"
    },

    "client_month_total_gst": {
        "examples": [
            "count total gst of <party> in <month>",
            "total gst of <party> in december",
            "gst amount of <party> in may"
        ],
        "requires_db": True,
        "requires_party": True,
        "requires_month": True,
        "collection": "bills",
        "operation": "sum gst fields by month",
        "handler": "handle_client_month_total_gst"
    },

    "client_pending_bills": {
        "examples": [
            "pending bills of <party>",
            "due bills of <party>",
            "overdue bills of <party>",
            "unpaid bills of <party>"
        ],
        "requires_db": True,
        "requires_party": True,
        "collection": "bills",
        "operation": "list pending bills",
        "handler": "handle_client_pending_bills"
    },

    "client_month_pending_bills": {
        "examples": [
            "pending bills of <party> in <month>",
            "due bills of <party> in <month>",
            "overdue bills of <party> in december",
            "unpaid bills of <party> in may"
        ],
        "requires_db": True,
        "requires_party": True,
        "requires_month": True,
        "collection": "bills",
        "operation": "list pending bills by month",
        "handler": "handle_client_month_pending_bills"
    }

    ,"general_rag": {
        "patterns": [
            "explain",
            "summarize",
            "what does",
            "why",
            "help me understand"
        ],
        "requires_db": False,
        "requires_party": False,
        "collection": "rag",
        "operation": "general explanation",
        "handler": "rag"
    }
}

# Synonyms dictionary for handling typos and variations
SYNONYMS = {
    "received": ["receive", "recive", "received", "recived", "collection", "payment received"],
    "pending": ["pending", "due", "overdue", "unpaid", "remaining", "balance"],
    "bill": ["bill", "bills", "biils", "invoice", "invoices"],
    "count": ["count", "number", "no", "no.", "total number", "how many"],
    "amount": ["amount", "amout", "total amount", "value"],
    "party": ["party", "client", "customer", "company"],
    "gst": ["gst", "tax", "cgst", "sgst", "igst"]
}

# Reverse mapping: typo/synonym -> canonical form
SYNONYM_REVERSE = {}
for canonical, variations in SYNONYMS.items():
    for var in variations:
        SYNONYM_REVERSE[var.lower()] = canonical

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


class IntentBlockService:
    """Service for intent detection using structured intent blocks with fuzzy matching"""

    @staticmethod
    def _similarity(left: str, right: str) -> int:
        """Return a 0-100 similarity score using rapidfuzz when available, else a stdlib fallback."""
        if fuzz is not None:
            try:
                return int(fuzz.token_set_ratio(left, right))
            except Exception:
                pass
        return int(SequenceMatcher(None, left, right).ratio() * 100)

    @staticmethod
    def fuzzy_match_word(word: str, candidates: List[str], threshold: int = 80) -> Optional[str]:
        """
        Fuzzy match a word (possibly with typo) to a list of candidates.
        Returns the best match if score >= threshold, else None.
        """
        if not word or not candidates:
            return None

        word_lower = word.lower()
        best_match = None
        best_score = 0

        for candidate in candidates:
            candidate_lower = candidate.lower()
            score = IntentBlockService._similarity(word_lower, candidate_lower)
            if score > best_score:
                best_score = score
                best_match = candidate

        return best_match if best_score >= threshold else None

    @staticmethod
    def normalize_message(message: str) -> str:
        """
        Normalize and fix common typos while keeping the original phrasing readable.
        The normalized message is used for intent matching; the original message is
        still used later for party extraction.
        """
        if not message:
            return message

        text = message.lower().strip()

        # Replace multi-word phrases first so "payment received" maps cleanly.
        phrase_variations = []
        for canonical, variations in SYNONYMS.items():
            for variation in variations:
                if ' ' in variation:
                    phrase_variations.append((variation, canonical))

        for variation, canonical in sorted(phrase_variations, key=lambda item: len(item[0]), reverse=True):
            text = re.sub(rf'\b{re.escape(variation)}\b', canonical, text)

        words = text.split()
        normalized_words = []
        all_single_word_variations = [
            variation
            for variations in SYNONYMS.values()
            for variation in variations
            if ' ' not in variation
        ]

        for word in words:
            clean_word = re.sub(r'[^a-z0-9]', '', word)
            if not clean_word:
                continue

            if clean_word in SYNONYM_REVERSE:
                normalized_words.append(SYNONYM_REVERSE[clean_word])
                continue

            match = IntentBlockService.fuzzy_match_word(clean_word, all_single_word_variations, threshold=75)
            if match:
                normalized_words.append(SYNONYM_REVERSE.get(match.lower(), match.lower()))
            else:
                normalized_words.append(clean_word)

        text = ' '.join(normalized_words)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _has_party_hint(message: str) -> bool:
        """Detect whether a query is likely party-scoped."""
        text = (message or '').lower()
        if re.search(r'\b(of|for)\s+[a-z0-9]', text):
            return True
        if re.search(r'\b(client|customer|company|party|vendor)\b', text):
            return True
        return False

    @staticmethod
    def _month_in_message(message: str) -> bool:
        """Check whether a month is mentioned in the message."""
        text = (message or '').lower()
        return any(month in text for month in MONTH_NAME_LOOKUP)

    @staticmethod
    def _pattern_to_regex(pattern: str) -> str:
        """Convert an intent pattern with placeholders into a permissive regex."""
        marker_safe = pattern.lower().replace('<party>', 'zzpartyzz').replace('<month>', 'zzmonthzz')
        normalized_pattern = IntentBlockService.normalize_message(marker_safe)
        normalized_pattern = normalized_pattern.replace('zzpartyzz', '<party>').replace('zzmonthzz', '<month>')

        month_regex = (
            r'(?P<month>january|february|march|april|may|june|july|august|september|sept|'
            r'october|oct|november|december|jan|feb|mar|apr|jun|jul|aug|sep|nov|dec)(?:\s+month)?'
        )
        party_regex = r'(?P<party>[a-z0-9&.,()\-/ ]{2,}?)'

        tokens = normalized_pattern.split()
        regex_tokens = []
        for token in tokens:
            if token == '<party>':
                regex_tokens.append(party_regex)
            elif token == '<month>':
                regex_tokens.append(month_regex)
            else:
                regex_tokens.append(re.escape(token))

        return r'\b' + r'\s+'.join(regex_tokens) + r'\b'

    @staticmethod
    def _matches_pattern(text: str, pattern: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Match a normalized message against a single intent pattern."""
        raw_pattern = (pattern or '').strip().lower()
        if not raw_pattern:
            return False, None, None

        if '<party>' in raw_pattern or '<month>' in raw_pattern:
            regex = IntentBlockService._pattern_to_regex(raw_pattern)
            match = re.search(regex, text)
            if not match:
                return False, None, None
            return True, match.groupdict().get('party'), match.groupdict().get('month')

        pattern = IntentBlockService.normalize_message(raw_pattern)

        if pattern in text:
            return True, None, None

        score = IntentBlockService._similarity(text, pattern)
        return (score >= 93), None, None

    @staticmethod
    def classify_intent_from_blocks(message: str) -> Tuple[Optional[str], int]:
        """
        Classify intent using a global-first intent block matcher.
        Returns (intent_name, confidence_score).
        """
        if not message:
            return None, 0

        normalized = IntentBlockService.normalize_message(message)
        text = re.sub(r'\s+', ' ', normalized.lower().strip())

        ordered_intents = [
            'greeting',
            'total_received_amount',
            'global_total_pending_amount',
            'global_pending_bills_list',
            'global_pending_bill_count',
            'global_month_bill_count',
            'client_month_bill_count',
            'client_month_pending_bills',
            'client_pending_amount',
            'client_pending_bills',
            'client_bill_count',
            'client_total_billing',
            'client_month_total_billing',
            'client_statement_entry_count',
            'client_total_gst',
            'client_month_total_gst',
            'general_rag',
        ]

        best_intent = None
        best_score = 0

        for intent_name in ordered_intents:
            config = INTENT_BLOCK.get(intent_name) or {}
            patterns = config.get('patterns') or config.get('examples') or []

            for pattern in patterns:
                matched, _, _ = IntentBlockService._matches_pattern(text, pattern)
                if not matched:
                    continue

                score = 100 if '<party>' not in pattern and '<month>' not in pattern else 92

                # Global intents must win before any party-scoped intent.
                if intent_name.startswith('global_') or intent_name == 'greeting' or intent_name == 'total_received_amount':
                    score = min(score + 5, 100)

                if score > best_score:
                    best_score = score
                    best_intent = intent_name

                # Exact match is enough for this intent.
                break

            if best_intent == intent_name and best_score >= 90:
                break

        if best_intent is None:
            return 'general_rag', 0

        return best_intent, best_score

    @staticmethod
    def extract_intent_requirements(intent_name: Optional[str]) -> Dict:
        """
        Extract configuration requirements for an intent.
        Returns a dict with metadata about what the intent needs.
        """
        if not intent_name or intent_name not in INTENT_BLOCK:
            return {
                "intent": None,
                "requires_db": False,
                "requires_party": False,
                "requires_month": False,
                "handler": None,
                "collection": None,
                "operation": None,
            }

        config = INTENT_BLOCK[intent_name]
        return {
            "intent": intent_name,
            "requires_db": config.get("requires_db", False),
            "requires_party": config.get("requires_party", False),
            "requires_month": config.get("requires_month", False),
            "handler": config.get("handler"),
            "collection": config.get("collection"),
            "operation": config.get("operation"),
        }

    @staticmethod
    def has_party_placeholder(examples: List[str]) -> bool:
        """Check if intent examples contain <party> placeholder."""
        return any("<party>" in ex for ex in examples)

    @staticmethod
    def has_month_placeholder(examples: List[str]) -> bool:
        """Check if intent examples contain <month> placeholder."""
        return any("<month>" in ex for ex in examples)

    @staticmethod
    def extract_party_from_message(message: str) -> Optional[str]:
        """
        Extract party/client name from message.
        Handles patterns like "of <party>", "for <party>", etc.
        """
        if not message:
            return None

        # Pattern 1: "of <party>"
        match = re.search(r'\bof\s+([A-Za-z][A-Za-z0-9&.,()\-/ ]{2,}?)(?:\s+(?:in|till|till date|to date|in fiscal))?$', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Pattern 2: "for <party>"
        match = re.search(r'\bfor\s+([A-Za-z][A-Za-z0-9&.,()\-/ ]{2,}?)(?:\s+(?:in|till|till date))?$', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Pattern 3: "<party> in <month>"
        match = re.search(r'\s+([A-Za-z][A-Za-z0-9&.,()\-/ ]{2,}?)\s+in\s+(?:month of\s+)?([A-Za-z]+)', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    @staticmethod
    def extract_month_from_message(message: str) -> Optional[int]:
        """
        Extract month from message.
        Returns month number (1-12) or None.
        """
        if not message:
            return None

        text_lower = message.lower()

        # Check for month names
        for month_name, month_num in MONTH_NAME_LOOKUP.items():
            if month_name in text_lower:
                return month_num

        # Check for numeric formats (05/2025, 5-2025, etc.)
        match = re.search(r'\b(0?[1-9]|1[0-2])\s*[/.-]', text_lower)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def should_use_database(intent_name: Optional[str]) -> bool:
        """
        Determine if the intent should be handled by database queries.
        """
        if not intent_name or intent_name not in INTENT_BLOCK:
            return False
        return INTENT_BLOCK[intent_name].get("requires_db", False)

    @staticmethod
    def should_use_rag(intent_name: Optional[str]) -> bool:
        """
        Determine if the intent should be handled by RAG.
        If no intent or intent doesn't require DB, use RAG.
        """
        return not IntentBlockService.should_use_database(intent_name)


# Export public functions for easy access
def normalize_message(message: str) -> str:
    """Normalize message by fixing common typos using fuzzy matching."""
    return IntentBlockService.normalize_message(message)


def classify_intent(message: str) -> Tuple[Optional[str], int]:
    """Classify user message intent using intent blocks."""
    return IntentBlockService.classify_intent_from_blocks(message)


def get_intent_config(intent_name: Optional[str]) -> Dict:
    """Get configuration for an intent."""
    return IntentBlockService.extract_intent_requirements(intent_name)


def extract_party(message: str) -> Optional[str]:
    """Extract party name from message."""
    return IntentBlockService.extract_party_from_message(message)


def extract_month(message: str) -> Optional[int]:
    """Extract month from message."""
    return IntentBlockService.extract_month_from_message(message)
