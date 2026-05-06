# Intent Block System - Test Cases & Examples

## Quick Test Cases

### Test 1: Typo Correction
```
Input:    "total recive amout till date"
Expected: Intent=total_received_amount, Confidence=95+%
Result:   ✓ Should return total payment amount from DB
```

### Test 2: Synonym Matching
```
Input:    "how many biils of ABC Company"
Expected: Intent=client_bill_count, Confidence=90+%
Result:   ✓ Should return invoice count for ABC Company
```

### Test 3: Multiple Typos
```
Input:    "pending amout of enviro for may"
Expected: Intent=client_month_pending_bills, Confidence=85+%
Result:   ✓ Should extract party="Enviro", month=May
```

### Test 4: Party Extraction
```
Input:    "due amount of Enviro Control Private Limited"
Expected: Party extracted as "Enviro Control Private Limited"
Result:   ✓ Should match to company in database
```

### Test 5: General Query Fallback
```
Input:    "What payment methods do you support"
Expected: Intent=general_rag, Confidence<60%
Result:   ✓ Should use RAG/LLM for response
```

---

## Real Query Examples

### Query Set 1: Global Queries (No Party Needed)

#### 1.1 Total Received
```
Variations:
- "total received amount till date"
- "total recive amout"  ← typo
- "collection amount"
- "payment received till date"
- "how much we recieved"  ← typo

Expected Response: "Total received amount: ₹X,XX,XXX (source: database)"
```

#### 1.2 Pending Amount
```
Variations:
- "what is total pending amount"
- "total outstanding"
- "total balance"
- "how much is pending"

Expected Response: "Total pending amount: ₹X,XX,XXX (source: database)"
```

#### 1.3 Greeting
```
Variations:
- "Hi"
- "Hello"
- "Hellow"  ← typo
- "How are you"
- "Hey there"

Expected Response: "Hello! I'm here to help with your payment queries."
```

---

### Query Set 2: Client-Specific Queries

#### 2.1 Client Pending Amount
```
Variations:
- "pending amount of ABC Company"
- "due amout of ABC"  ← typos
- "how much pending for ABC Company"
- "balance of Enviro Control"
- "outstanding for ABC Company"

Expected Response: "Pending amount for ABC Company: ₹X,XX,XXX"
```

#### 2.2 Client Bill Count
```
Variations:
- "how many bills of ABC Company"
- "number of invoices of ABC"
- "count biils of ABC"  ← typo
- "total invoices of Enviro Control"
- "how many invoices of ABC Company"

Expected Response: "ABC Company has 15 invoices in this fiscal year"
```

#### 2.3 Client Total Billing
```
Variations:
- "total billing of ABC Company till date"
- "total invoice amout of ABC"  ← typo
- "grand total of Enviro Control"
- "total billed to ABC Company"

Expected Response: "Total billing for ABC Company: ₹X,XX,XXX"
```

#### 2.4 Client Total GST
```
Variations:
- "total GST of ABC Company"
- "gst amout of ABC"  ← typo
- "total tax of Enviro Control"
- "how much gst for ABC Company"

Expected Response: "Total GST for ABC Company: ₹XX,XXX"
```

#### 2.5 Client Pending Bills List
```
Variations:
- "pending bills of ABC Company"
- "due biils of ABC"  ← typo
- "unpaid invoices of Enviro Control"
- "list pending bills of ABC"

Expected Response: 
"Pending bills for ABC Company:
- INV-001 | 2025-05-10 | ₹5,000
- INV-005 | 2025-05-15 | ₹8,000
...
Total Pending: ₹XX,XXX"
```

---

### Query Set 3: Time-Based Queries

#### 3.1 Bills in Month
```
Variations:
- "how many bills of ABC in May"
- "total biils of ABC in may"  ← typo
- "invoice count of Enviro in december"
- "bills of ABC in 05/2025"

Expected Response: "ABC Company has 5 invoices in May 2025"
```

#### 3.2 Billing in Month
```
Variations:
- "total billing of ABC in May"
- "invoice amout of ABC in may"  ← typo
- "billing of Enviro in december"
- "total billed to ABC in 05/2025"

Expected Response: "Total billing for ABC in May: ₹45,000"
```

#### 3.3 Pending in Month
```
Variations:
- "pending bills of ABC in May"
- "due biils of ABC in may"  ← typo
- "pending amount of Enviro in december"
- "outstanding for ABC in 05/2025"

Expected Response: 
"Pending for ABC in May:
- INV-003 | ₹3,000
- INV-004 | ₹2,000
Total Pending: ₹5,000"
```

#### 3.4 GST in Month
```
Variations:
- "total GST of ABC in May"
- "gst amout of ABC in may"  ← typo
- "tax for Enviro in december"
- "total tax of ABC in 05/2025"

Expected Response: "Total GST for ABC in May: ₹7,500"
```

---

### Query Set 4: Edge Cases & Fallbacks

#### 4.1 Ambiguous Query
```
Input: "pending amount"
Expected: Should ask "Which party? (ABC Company, Enviro Control, etc.)"
Because: No party specified, but intent requires it
```

#### 4.2 Unknown Client
```
Input: "pending of XYZ Corporation"
Expected: Should return "0 invoices found" or ask to clarify
Because: Client not in database
```

#### 4.3 Misspelled Client
```
Input: "pending of Enviro Control"  ← missing 'r'
Expected: Should suggest closest match with confidence score
Because: Fuzzy matching will find "Enviro Control"
```

#### 4.4 Multiple Typos
```
Input: "totall gst of ABc Company in Mey"  ← typos
Expected: Should normalize and match to intent
Because: Fuzzy matching handles multiple errors
```

#### 4.5 General Question
```
Input: "How do I make a payment?"
Expected: Should use RAG/LLM for response
Because: Doesn't match any structured intent
```

---

## Test Script Examples

### Python Test (For Developers)

```python
from app.services.intent_block_service import classify_intent, extract_party, extract_month

# Test 1: Typo Correction
intent, conf = classify_intent("total recive amout till date")
assert intent == "total_received_amount"
assert conf > 90
print("✓ Test 1 passed")

# Test 2: Party Extraction
party = extract_party("pending of ABC Company")
assert party == "ABC Company"
print("✓ Test 2 passed")

# Test 3: Month Extraction
month = extract_month("pending in may")
assert month == 5
print("✓ Test 3 passed")

# Test 4: Complex Query
intent, conf = classify_intent("how many biils of ABC in may")
party = extract_party("how many biils of ABC in may")
month = extract_month("how many biils of ABC in may")
assert intent == "client_month_bill_count"
assert party == "ABC"
assert month == 5
print("✓ Test 4 passed")
```

### API Test (Using curl)

```bash
# Test 1: Total Received with Typo
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "total recive amout till date"}'

# Test 2: Client Pending with Party
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pending amout of ABC Company"}'

# Test 3: Greeting
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hellow"}'

# Test 4: Complex Query
curl -X POST http://localhost:8000/api/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "total gst of ABC Company in may"}'
```

---

## Expected Responses Format

### Success (Database)
```json
{
  "response": "Total pending amount: ₹2,50,000",
  "context_summary": {
    "fiscal_year": "FY-2025-2026",
    "party_name": "ABC Company",
    "total_pending": 250000
  },
  "tokens_used": 0
}
```

### Success (RAG)
```json
{
  "response": "We support multiple payment methods including NEFT, RTGS, UPI, CHEQUE...",
  "context_summary": {
    "docs_retrieved": 3,
    "fiscal_year": "FY-2025-2026"
  },
  "tokens_used": 245
}
```

### Clarification Needed
```json
{
  "response": "Please specify which client/party you mean",
  "context_summary": {
    "extracted": "ABC",
    "candidates": [
      "ABC Company (92)",
      "ABC Traders (78)"
    ]
  },
  "tokens_used": 0
}
```

### Not Found
```json
{
  "response": "No invoices found for this client in the selected fiscal year",
  "context_summary": {
    "party_name": "Unknown Company",
    "fiscal_year": "FY-2025-2026"
  },
  "tokens_used": 0
}
```

---

## Performance Baselines

Expected performance metrics:
- **Intent Classification**: < 50ms
- **Fuzzy Matching**: < 10ms per word
- **Party Extraction**: < 5ms
- **Database Query**: 100-500ms depending on data size
- **RAG Generation**: 1-3 seconds (LLM dependent)

---

## Regression Testing Checklist

Before deploying, verify:
- [ ] All 12 intents recognize their example queries
- [ ] Typo correction works for all SYNONYMS
- [ ] Party names extracted correctly
- [ ] Months extracted correctly
- [ ] Database routing working for structured intents
- [ ] RAG fallback working for general questions
- [ ] Confidence scores reasonable (60-100%)
- [ ] Error handling for missing/invalid data
- [ ] Logging shows classification details
- [ ] No performance degradation

---

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Intent Classification
```python
from app.services.intent_block_service import classify_intent

message = "your test message"
intent, conf = classify_intent(message)
print(f"Intent: {intent}")
print(f"Confidence: {conf}")
```

### Check Message Normalization
```python
from app.services.intent_block_service import normalize_message

message = "total recive amout"
normalized = normalize_message(message)
print(f"Original: {message}")
print(f"Normalized: {normalized}")
```

### Check Entity Extraction
```python
from app.services.intent_block_service import extract_party, extract_month

message = "pending of ABC Company in May"
party = extract_party(message)
month = extract_month(message)
print(f"Party: {party}")
print(f"Month: {month}")
```

