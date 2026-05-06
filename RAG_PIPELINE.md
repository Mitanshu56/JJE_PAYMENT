# RAG Pipeline for Payment Chatbot

## Overview
Retrieval-Augmented Generation (RAG) combines data retrieval with LLM to provide accurate, context-aware responses about bills and payments.

---

## Architecture

```
User Query (e.g., "Show my overdue bills")
    ↓
[1. QUERY EMBEDDING] → Convert to vector using embedding model
    ↓
[2. VECTOR RETRIEVAL] → Search vector DB for similar documents (bills/payments)
    ↓
[3. CONTEXT ASSEMBLY] → Extract top-K relevant documents from MongoDB
    ↓
[4. PROMPT INJECTION] → Combine system prompt + retrieved context + user query
    ↓
[5. LLM PROCESSING] → Send to OpenAI/LLM for generation
    ↓
[6. RESPONSE] → Return answer to user
```

---

## Implementation Steps

### **Step 1: Data Preparation (MongoDB → Embeddings)**

**Extract from MongoDB:**
```
bills collection → Extract: bill_id, amount, due_date, status
payments collection → Extract: payment_id, amount, date, bill_id
fiscal_years → Track: FY context
```

**Create document chunks:**
```
Doc 1: "Bill #12345 for $5000 due on 2026-06-15 - OVERDUE - Fiscal Year 2025-2026"
Doc 2: "Payment $2000 on 2026-05-01 applied to Bill #12345"
Doc 3: "Total outstanding: $15000 across 8 bills in FY 2025-2026"
```

---

### **Step 2: Embedding Generation**

**Model**: `text-embedding-ada-002` (OpenAI) or `all-MiniLM-L6-v2` (open-source)

**Process:**
```
Doc → Embedding Model → 1536-dim vector
```

**Store:**
```
{
  "doc_id": "bill_12345",
  "content": "Bill #12345 for $5000 due on 2026-06-15...",
  "embedding": [0.123, -0.456, 0.789, ...],  // 1536 dimensions
  "metadata": {
    "collection": "bills",
    "fy": "2025-2026",
    "user_id": "user_123"
  }
}
```

---

### **Step 3: Vector Storage & Retrieval**

**Option A: FAISS (Local, Recommended for Dev)**
```python
import faiss
import numpy as np

# Create index
index = faiss.IndexFlatL2(1536)  # 1536 = ada embedding dims

# Add vectors
embeddings = np.array([...])  # N x 1536
index.add(embeddings)

# Search
query_embedding = get_embedding("Show my bills")
distances, indices = index.search(query_embedding.reshape(1, -1), k=5)
# Returns top 5 most similar documents
```

**Option B: Pinecone (Cloud, Scalable)**
```python
import pinecone

pinecone.init(api_key="your-api-key", environment="us-west1-gcp")
index = pinecone.Index("payment-chatbot")

# Upsert (store)
index.upsert(vectors=[
    ("bill_12345", embedding, {"fy": "2025-2026", "amount": 5000})
])

# Query
results = index.query(query_embedding, top_k=5, include_metadata=True)
```

---

### **Step 4: Prompt Injection (Context Assembly)**

**System Prompt (Role Definition):**
```
You are a helpful payment system assistant. You have access to:
- Bills database (bill amounts, due dates, status)
- Payments history (payment dates, amounts)
- Fiscal year information

Answer user questions accurately based on retrieved data.
Always cite bill IDs and amounts.
Be concise and helpful.
```

**Retrieval Prompt Template:**
```
CONTEXT:
{retrieved_bills_and_payments}

USER QUESTION:
{user_query}

Based on the context above, answer the question. If information is not available, say so.

ANSWER:
```

**Full Injection Example:**
```
SYSTEM: You are a payment system assistant with access to bills and payments data.

CONTEXT:
Bill #12345: $5000 due 2026-06-15 - OVERDUE (FY 2025-2026)
Bill #12346: $3000 due 2026-07-20 - PAID (FY 2025-2026)
Payment $5000 on 2026-05-10 to Bill #12346
Total bills in FY 2025-2026: $25,000
Total paid: $15,000

USER: Show me my overdue bills

ASSISTANT: Based on your account:
- You have 1 overdue bill: Bill #12345 for $5000, due on 2026-06-15
This is the only outstanding bill in your current fiscal year.
```

---

### **Step 5: LLM Model Selection**

| Model | Cost | Quality | Speed | Best For |
|-------|------|---------|-------|----------|
| **gpt-4** | $0.03/1K tokens | Excellent | Slower | Complex reasoning |
| **gpt-3.5-turbo** | $0.0005/1K tokens | Good | Fast | Quick responses |
| **Llama 2 (70B)** | Self-hosted | Good | Medium | Privacy-focused |
| **Mistral 7B** | Self-hosted | Good | Fast | Resource-efficient |

**Recommended for your system: `gpt-3.5-turbo`** (fast, cheap, good quality)

---

### **Step 6: Response Generation**

**LLM Call:**
```python
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{CONTEXT}\n\n{user_query}"}
    ],
    temperature=0.7,  # Balance creativity & consistency
    max_tokens=500
)
```

---

## Prompt Engineering Best Practices

### **1. System Role Definition**
```
"You are an expert financial assistant for a payment management system..."
```

### **2. Few-Shot Examples (In-Context Learning)**
```
EXAMPLE 1:
User: "How many bills am I overdue on?"
Context: Bill #1 (OVERDUE), Bill #2 (PAID), Bill #3 (OVERDUE)
Response: "You have 2 overdue bills: #1 and #3. Total due: $8000"

USER QUESTION: {user_query}
CONTEXT: {retrieved_data}
```

### **3. Output Format Specification**
```
"Format your response as:
- List overdue bills with amounts
- Total amount due
- Suggested action (e.g., 'Payment due by June 15')"
```

### **4. Constraint Instructions**
```
"If the user asks for something outside bills/payments:
- Say: 'I can only help with bill and payment information'
- Do not generate financial advice"
```

### **5. Context Prioritization**
```
"Use the most recent data first.
If multiple bills match, prioritize OVERDUE, then DUE SOON, then PAID."
```

---

## Data Flow Diagram

```
MongoDB (Bills, Payments, FY)
    ↓
[Data Extraction Service]
    ↓
Create Documents with Metadata
    ↓
Embedding Model (OpenAI or Local)
    ↓
Vector Store (FAISS/Pinecone)
    ↓
    
User Query → 
    ↓
[FastAPI Endpoint] 
    ↓
Query Embedding
    ↓
Retrieve Top-5 Docs from Vector Store
    ↓
Fetch Full Data from MongoDB
    ↓
Build Context + Prompt Injection
    ↓
OpenAI API (gpt-3.5-turbo)
    ↓
Response → Frontend → User
```

---

## Implementation Checklist

- [ ] Step 1: Extract MongoDB data & create documents
- [ ] Step 2: Generate embeddings & store in vector DB
- [ ] Step 3: Create retrieval function
- [ ] Step 4: Build prompt injection template
- [ ] Step 5: Implement LLM integration (OpenAI)
- [ ] Step 6: Create FastAPI endpoint `/chat`
- [ ] Step 7: Add React chat component
- [ ] Step 8: Test end-to-end
- [ ] Step 9: Add conversation history (optional)
- [ ] Step 10: Deploy

---

## Technologies Used

| Component | Technology |
|-----------|-----------|
| **Embedding Model** | text-embedding-ada-002 (OpenAI) |
| **Vector DB** | FAISS (local) or Pinecone (cloud) |
| **LLM** | gpt-3.5-turbo (OpenAI) |
| **Backend** | FastAPI |
| **Frontend** | React |
| **Data Storage** | MongoDB |
| **Python Library** | `langchain` (optional, simplifies RAG) |

---

## Dependencies to Add

```
openai==1.3.0
faiss-cpu==1.7.4
langchain==0.1.0
sentence-transformers==2.2.2
```

---

## Security & Best Practices

1. **API Key Management**: Store OpenAI key in `.env`
2. **Rate Limiting**: Limit API calls to prevent abuse
3. **User Isolation**: Filter retrieved documents by user/FY via metadata
4. **Cost Control**: Set max tokens to prevent runaway costs
5. **Error Handling**: Gracefully handle API failures
6. **Caching**: Cache common queries to reduce costs

---

## Cost Estimation (Monthly)

- **Embeddings**: 1000 docs × $0.0001 = $0.10
- **Queries**: 100 chats × $0.002/query = $0.20
- **Vector DB**: FAISS (free) or Pinecone ($25+)
- **Total**: ~$0.30 (FAISS) to $25+ (Pinecone)

**Recommendation**: Start with FAISS (free), upgrade to Pinecone if scale needed.

