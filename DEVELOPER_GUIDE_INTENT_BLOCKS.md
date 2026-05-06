# Intent Block System - Developer Guide

## Quick Start

The Intent Block system is located in:
```
backend/app/services/intent_block_service.py
```

## How to Add a New Intent

### Step 1: Define the Intent in INTENT_BLOCK

```python
INTENT_BLOCK = {
    # ... existing intents ...
    
    "my_new_intent": {
        "examples": [
            "example query 1",
            "example query 2",
            "example with <party>",
            "example with <month>"
        ],
        "requires_db": True,           # True if needs database queries
        "requires_party": False,       # True if needs client name
        "requires_month": False,       # True if needs month
        "collection": "bills",         # Which collection to query
        "operation": "sum amount",     # What operation to perform
        "handler": "handle_my_intent"  # Handler function name
    }
}
```

### Step 2: Add Examples (for better matching)

Use `<party>` and `<month>` placeholders for dynamic queries:

```python
"examples": [
    "how many pending invoices",
    "pending invoice count of <party>",
    "pending invoices of <party> in <month>",
    "pending biils",  # Include typos to test fuzzy matching!
]
```

### Step 3: Add Synonyms (optional)

To handle common misspellings, add to SYNONYMS:

```python
SYNONYMS = {
    # ... existing synonyms ...
    "invoices": ["invoices", "invoices", "invoises", "bills"],  # Common typo
    "status": ["status", "state", "condition"],
}
```

### Step 4: Implement the Handler

In `chatbot_routes.py`, add a handler function:

```python
async def handle_my_intent(
    db: AsyncIOMotorDatabase, 
    message: str, 
    fiscal_year: str,
    party_name: Optional[str] = None,
    month: Optional[int] = None
) -> dict:
    """
    Handle the my_new_intent query.
    
    Args:
        db: MongoDB connection
        message: User's original message
        fiscal_year: Currently selected fiscal year
        party_name: Extracted party name (if requires_party=True)
        month: Extracted month (if requires_month=True)
    
    Returns:
        Response dict with keys:
            - status: 'success', 'error', 'clarify', 'not_found'
            - response: Message to user
            - context_summary: Dict with query details
            - tokens_used: Number of tokens (0 for DB queries)
            - source: 'database'
    """
    try:
        base_filter = {}
        if fiscal_year:
            base_filter['fiscal_year'] = fiscal_year
        
        # Add your query logic here
        result = await db['bills'].count_documents(base_filter)
        
        return {
            'status': 'success',
            'response': f'Found {result} records',
            'context_summary': {'count': result},
            'tokens_used': 0,
            'source': 'database',
        }
    except Exception as e:
        logger.exception(f"Error in handle_my_intent: {e}")
        return {
            'status': 'error',
            'response': 'Error processing your query',
            'context_summary': {},
            'tokens_used': 0,
            'source': 'database',
        }
```

### Step 5: Register Handler in _query_database_answer

Add to the `_query_database_answer` function:

```python
async def _query_database_answer(db, message, fiscal_year):
    # ... existing code ...
    
    intent = intent_info.get('intent')
    
    # Add your handler call
    if intent == 'my_new_intent':
        party_name = intent_info.get('extracted_party')
        month = intent_info.get('extracted_month')
        return await handle_my_intent(db, message, fiscal_year, party_name, month)
    
    # ... rest of handlers ...
```

---

## Understanding Fuzzy Matching

### How It Works

```python
from intent_block_service import IntentBlockService

# Example: Correct a typo
word = "recive"
candidates = ["received", "receive", "collection"]
match = IntentBlockService.fuzzy_match_word(word, candidates, threshold=80)
# Returns: "received"

# Example: Normalize a full message
message = "total recive amout of ABC Company"
normalized = IntentBlockService.normalize_message(message)
# Returns: "total received amount of abc company"
```

### Threshold Values

- **90-100**: Exact or very close match
- **80-89**: Likely typo correction
- **70-79**: Partial match (use with caution)
- **<70**: Too different, not a match

---

## Intent Classification Flow

```python
from intent_block_service import IntentBlockService

# Classify a user message
intent_name, confidence = IntentBlockService.classify_intent_from_blocks(message)

# Get intent configuration
config = IntentBlockService.extract_intent_requirements(intent_name)

# Extract required info
party = IntentBlockService.extract_party_from_message(message)
month = IntentBlockService.extract_month_from_message(message)
```

---

## Testing Your Intent

### Unit Test Example

```python
import pytest
from app.services.intent_block_service import classify_intent, INTENT_BLOCK

def test_my_new_intent_classification():
    # Test exact match
    intent, conf = classify_intent("example query 1")
    assert intent == "my_new_intent"
    assert conf >= 90
    
    # Test with typo
    intent, conf = classify_intent("exampl query 1")  # 'exampl' typo
    assert intent == "my_new_intent"
    assert conf >= 75
    
    # Test with party extraction
    intent, conf = classify_intent("query of ABC Company")
    assert intent == "my_new_intent"
    assert extract_party("query of ABC Company") == "ABC Company"
```

### Manual Testing

```bash
# Start backend
cd backend
python -m uvicorn app.main:app --reload

# Test via API
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "total recive amout till date"}'
```

---

## Advanced: Custom Operations

Define custom operations in your handler:

```python
# Operation: "sum amount"
total = sum(float(doc.get('amount', 0)) for doc in docs)

# Operation: "count bills"
count = len(docs)

# Operation: "list pending bills"
pending = [d for d in docs if d.get('remaining_amount', 0) > 0]

# Operation: "sum gst fields"
total_gst = sum(
    float(doc.get('cgst', 0)) + 
    float(doc.get('sgst', 0)) + 
    float(doc.get('igst', 0))
    for doc in docs
)
```

---

## Debugging Intent Classification

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run:
from intent_block_service import classify_intent
intent, conf = classify_intent("your test message")
# See detailed logs for debugging
```

---

## Performance Tips

1. **Cache Classifications**: For repeated queries, cache intent classifications
2. **Batch Operations**: Use MongoDB's aggregation pipeline for complex queries
3. **Limit Results**: Use `.to_list(length=5000)` to avoid loading entire collections
4. **Index Fields**: Ensure MongoDB indexes on `party_name`, `fiscal_year`, `invoice_date`

---

## Common Patterns

### Query All Bills for Party in Fiscal Year
```python
party_name = "ABC Company"
fiscal_year = "FY-2025-2026"

query = {
    'party_name': {'$regex': f'^{re.escape(party_name)}$', '$options': 'i'},
    'fiscal_year': fiscal_year
}

bills = await db['bills'].find(query).to_list(length=1000)
```

### Query Bills by Month
```python
from datetime import datetime

month = 5  # May
year = 2025

query = {
    'invoice_date': {
        '$gte': datetime(year, month, 1),
        '$lt': datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    }
}
```

### Sum Amounts with Filters
```python
docs = await db['bills'].find(query).to_list(length=5000)
total = sum(float(doc.get('remaining_amount', 0)) for doc in docs)
```

---

## Error Handling

Always include proper error handling:

```python
try:
    result = await db['bills'].find(query).to_list(length=1000)
except Exception as e:
    logger.exception(f"Database error: {e}")
    return {
        'status': 'error',
        'response': 'Error querying database',
        'context_summary': {},
        'tokens_used': 0,
        'source': 'database',
    }
```

---

## Extending Synonyms

Add more synonym variations for better typo handling:

```python
SYNONYMS = {
    "received": [
        "receive", "recive", "recievd",  # Common typos
        "received", "recived", 
        "collection", "payment received",
        "funds received", "money in"  # Variations
    ],
}
```

---

## Integration with RAG

If your intent should fall back to RAG for follow-up explanation:

```python
# Return success from database
db_result = {
    'status': 'success',
    'response': f'Total: ₹{amount}',
    'context_summary': {...},
    'source': 'database',
}

# Then optionally:
# rag_result = await rag_service.chat(
#     f"Explain why the total for {party_name} is ₹{amount}",
#     fiscal_year
# )
```

---

## Questions?

Refer to `INTENT_BLOCK_GUIDE.md` for user documentation or check existing handlers in `chatbot_routes.py` for examples.

