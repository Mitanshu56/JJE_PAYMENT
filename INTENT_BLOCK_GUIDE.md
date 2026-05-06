# Intent Block System - User Guide

## Overview

Your chatbot now uses a **structured Intent Block system** with **fuzzy matching** for intelligent query processing. This replaces traditional keyword matching with semantic understanding and typo tolerance.

## Features

### 1. **Typo Tolerance with Fuzzy Matching**
Common misspellings are automatically corrected:
- `recive` → `received`
- `biils` → `bills`
- `amout` → `amount`
- `hellow` → `hello`

### 2. **Structured Intent Recognition**
Each query type is defined as an "Intent Block" with:
- **Examples**: Sample queries that match this intent
- **Requirements**: DB access, party name, month, etc.
- **Handler**: Function to process the intent
- **Operation**: What data to retrieve (sum, count, list)

### 3. **Intelligent Routing**
Queries are routed to the appropriate handler:
- **Database queries**: For exact financial calculations
- **RAG queries**: For general questions and explanations

---

## How It Works

### Step 1: Message Normalization
Your message is checked for typos and normalized:

```
User Input:  "total recive amout till date"
            ↓ (fuzzy matching applied)
Normalized: "total received amount till date"
```

### Step 2: Intent Classification
The normalized message is matched against intent block examples using semantic similarity:

```
Message: "total received amount till date"
         ↓
Intent Match: "total_received_amount" (confidence: 95%)
         ↓
Routing: DATABASE (because requires_db = True)
```

### Step 3: Query Execution
The appropriate handler processes your query:

```
Intent: total_received_amount
Action: Sum all payment amounts from database
Result: "Total received amount: ₹2,50,000 (source: database)"
```

---

## Available Intents

### Global Queries (No Party Required)

#### 1. **Greeting**
```
Examples: "Hi", "Hello", "How are you"
Response: General greeting
Source: LLM (no database)
```

#### 2. **Total Received Amount**
```
Examples: 
  - "Tell me total received amount till date"
  - "Collection amount"
  - "Payment received till date"
Operation: Sum all payment amounts
```

#### 3. **Pending Bills Count**
```
Examples:
  - "How many pending bills?"
  - "Count pending invoices"
Operation: Count bills with pending amounts
```

#### 4. **Total Pending Amount** 
```
Examples:
  - "Total pending amount"
  - "Outstanding balance"
Operation: Sum remaining amounts across all bills
```

---

### Client-Specific Queries (Requires Party Name)

#### 5. **Client Pending Amount**
```
Examples:
  - "Pending amount of ABC Company"
  - "Due amount of Enviro Control"
  - "Balance amount of <party>"
Operation: Sum remaining amount for specific client
```

#### 6. **Client Bill Count**
```
Examples:
  - "Number of bills of ABC Company"
  - "Total invoices of Enviro Control"
  - "How many biils of <party>" ← typo fixed!
Operation: Count invoices for specific client
```

#### 7. **Client Total Billing**
```
Examples:
  - "Total billing of ABC Company till date"
  - "Total invoice amount of Enviro Control"
  - "Billing amout of <party>" ← typo fixed!
Operation: Sum invoice amounts for specific client
```

#### 8. **Client Total GST**
```
Examples:
  - "Total GST of ABC Company"
  - "Tax amount of Enviro Control"
Operation: Sum GST fields for specific client
```

#### 9. **Client Pending Bills List**
```
Examples:
  - "Pending bills of ABC Company"
  - "Due bills of Enviro Control"
  - "Unpaid bills of <party>"
Operation: List bills with pending amounts
```

---

### Time-Based Queries (Requires Month)

#### 10. **Client Month Bill Count**
```
Examples:
  - "Biils of ABC in May" ← typo fixed!
  - "Invoices of Enviro Control in december"
Operation: Count bills for specific month
```

#### 11. **Client Month Total Billing**
```
Examples:
  - "Total billing of ABC in May"
  - "Invoice amout of Enviro Control in december" ← typo fixed!
Operation: Sum billing for specific month
```

#### 12. **Client Month Total GST**
```
Examples:
  - "Total GST of ABC in May"
  - "Tax of Enviro Control in december"
Operation: Sum GST for specific month
```

---

## Query Examples & Typo Tolerance

### Example 1: Typo in "Received"
```
Input:  "what is total recive amout till date"
        ↓ (typos corrected)
Fixed:  "what is total received amount till date"
        ↓ (matched to intent)
Result: Total Received Amount = ₹2,50,000
```

### Example 2: Typo in "Bills"
```
Input:  "how many biils of ABC Company"
        ↓ (typos corrected)
Fixed:  "how many bills of ABC Company"
        ↓ (matched to intent)
Result: ABC Company has 15 invoices
```

### Example 3: Complex Query with Multiple Typos
```
Input:  "pending amout of enviro for may"
        ↓ (typos corrected)
Fixed:  "pending amount of enviro for may"
        ↓ (party extracted: "enviro", month: May)
Result: Pending amount for Enviro Control in May: ₹45,000
```

---

## Synonyms Reference

The system recognizes these synonyms and variations:

| Canonical | Variations |
|-----------|-----------|
| received | receive, recive, received, recived, collection, payment received |
| pending | pending, due, overdue, unpaid, remaining, balance |
| bill | bill, bills, biils, invoice, invoices |
| count | count, number, no, no., total number, how many |
| amount | amount, amout, total amount, value |
| party | party, client, customer, company |
| gst | gst, tax, cgst, sgst, igst |

---

## How to Use the Chatbot

### 1. **Upload Data First**
- Upload invoice Excel file via dashboard
- Upload bank statement Excel file via dashboard
- Run Payment Matching

### 2. **Ask Queries**
Ask any question about your payments and invoices. Typos are automatically fixed!

```
✓ "what is total recive amount" 
✓ "how many biils of ABC Company"
✓ "pending amout of Enviro"
✓ "total gst in may"
```

### 3. **Get Results**
Results include:
- **Answer**: The requested information
- **Source**: Whether data came from database or AI
- **Confidence**: How sure the system is about intent

---

## Tips for Better Results

1. **Be Specific**: "Pending amount of ABC Company" is better than "pending amount"
2. **Use Natural Language**: Don't worry about exact wording - synonyms work!
3. **Include Periods**: Mention "till date", "in May", etc. for better context
4. **Don't Worry About Typos**: "recive", "amout", "biils" are all understood!
5. **Mention Party Names**: If asking about a specific company, include its name

---

## Confidence Scores

The system shows how confident it is about your intent:

- **90-100%**: Very confident - exact match found
- **80-89%**: Confident - close match with fuzzy logic
- **70-79%**: Reasonable - matches core keywords  
- **60-69%**: Low confidence - might clarify with you
- **<60%**: Very low - will use general RAG

---

## Technical Details

### Intent Block Structure
```python
"intent_name": {
    "examples": [...],           # Sample queries
    "requires_db": True/False,   # Needs database
    "requires_party": True/False, # Needs client name
    "requires_month": True/False, # Needs month
    "handler": "function_name",   # Processing function
    "collection": "collection_name", # MongoDB collection
    "operation": "operation_type"    # What to do
}
```

### Fuzzy Matching Algorithm
- Uses token_set_ratio for semantic similarity
- Threshold: 75-80% for typo correction
- Supports partial matches and word order variations

---

## Architecture Flow

```
User Message
    ↓
[Step 1] Normalize
  - Apply fuzzy matching
  - Fix typos
  - Standardize format
    ↓
[Step 2] Classify Intent
  - Match against intent blocks
  - Calculate confidence
  - Extract party/month
    ↓
[Step 3] Route
  ├─ Database Intent?
  │  └─ Execute DB query
  │     └─ Return exact results
  │
  └─ General Intent?
     └─ Use RAG
        └─ Generate LLM response
    ↓
Response to User
```

---

## Troubleshooting

### "I could not find this client..."
- Check spelling of company name
- Ensure fiscal year is selected
- Make sure invoice data is uploaded

### "Not finding my query type..."
- Try rephrasing with synonyms
- Be more specific about what you want
- Include party name if applicable

### "Low confidence on my intent"
- Provide more context
- Use standard terms from the examples
- Avoid ambiguous phrasing

---

## Questions?

Refer to the **Intent Block definitions** in `backend/app/services/intent_block_service.py` for:
- Complete list of all intents
- All example queries
- Synonym mappings
- Configuration options

