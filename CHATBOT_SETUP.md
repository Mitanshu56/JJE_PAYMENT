# RAG Chatbot Setup & Usage Guide

## Quick Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New packages added:
- `openai==1.3.0` - LLM API
- `faiss-cpu==1.7.4` - Vector search
- `sentence-transformers==2.2.2` - Embeddings
- `langchain==0.1.0` - RAG framework
- `numpy==1.24.3` - Numerical operations

### 2. Configure Environment

Create/update `.env` in the backend directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002  # Optional, using local by default

# MongoDB
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=payment_tracking

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=False

# RAG Configuration
RAG_TOP_K=5
RAG_MAX_CONTEXT_TOKENS=2000
RAG_TEMPERATURE=0.7
```

### 3. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or login
3. Navigate to API Keys section
4. Create new secret key
5. Copy to `.env` file as `OPENAI_API_KEY`

**Cost**: ~$0.002 per query using gpt-3.5-turbo

### 4. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

All endpoints require authentication token via `Authorization: Bearer {token}` header.

### Initialize Data Index

**Endpoint**: `POST /api/chatbot/index`

**Request**:
```json
{
  "fiscal_year": "FY-2025-2026"
}
```

**Response**:
```json
{
  "status": "success",
  "count": 42,
  "message": "Successfully indexed 42 bills for fiscal year 'FY-2025-2026'"
}
```

**When to call**: 
- First time using chatbot for a fiscal year
- After bulk bill imports
- To refresh data

---

### Send Chat Message

**Endpoint**: `POST /api/chatbot/chat`

**Headers**:
```
Authorization: Bearer {token}
X-Fiscal-Year: FY-2025-2026
```

**Request**:
```json
{
  "message": "Show me my overdue bills",
  "include_context": true
}
```

**Response**:
```json
{
  "response": "You have 2 overdue bills:\n- Bill #12345 for $5,000.00 due on 2026-06-15\n- Bill #12346 for $3,000.00 due on 2026-06-10\n\nTotal overdue: $8,000.00",
  "context_summary": {
    "total_bills": 2,
    "total_amount": 8000,
    "status_breakdown": {"OVERDUE": 2},
    "avg_similarity": 0.95
  },
  "tokens_used": 145
}
```

**Query Parameters**:
- `include_context` - Include context summary in response (default: false)

---

### Get Conversation History

**Endpoint**: `GET /api/chatbot/history`

**Response**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Show my overdue bills",
      "timestamp": "2026-05-03T10:30:00"
    },
    {
      "role": "assistant",
      "content": "You have 2 overdue bills...",
      "timestamp": "2026-05-03T10:30:05"
    }
  ]
}
```

---

### Clear Conversation History

**Endpoint**: `POST /api/chatbot/history/clear`

**Response**:
```json
{
  "status": "success",
  "message": "Conversation history cleared"
}
```

---

### Get Pipeline Status

**Endpoint**: `GET /api/chatbot/status`

**Response**:
```json
{
  "status": "operational",
  "stats": {
    "vector_store": {
      "indexed_documents": 42,
      "embedding_dimension": 384,
      "model": "all-MiniLM-L6-v2"
    },
    "llm": {
      "model": "gpt-3.5-turbo",
      "temperature": 0.7,
      "max_tokens": 500
    },
    "history": {
      "messages": 5
    }
  },
  "message": "RAG chatbot is ready"
}
```

---

### Rebuild Vector Index

**Endpoint**: `POST /api/chatbot/rebuild-index`

**Parameters**:
- `fiscal_year` (required) - FY to rebuild

**Note**: Admin only

**Response**:
```json
{
  "status": "success",
  "count": 42,
  "message": "Successfully indexed 42 bills for fiscal year 'FY-2025-2026'"
}
```

---

## Example Queries for the Chatbot

```
1. "Show me my overdue bills"
   → Lists bills with OVERDUE status

2. "How much do I owe in total?"
   → Sums all outstanding bills

3. "Which bills are due this month?"
   → Filters bills by due date

4. "Tell me about bill #12345"
   → Details for specific bill

5. "When is my next payment due?"
   → Finds earliest due date

6. "Show me payment history"
   → Lists recent payments

7. "How many bills have I paid?"
   → Counts PAID bills

8. "What's my fiscal year?"
   → Returns current FY context
```

---

## Prompt Engineering Guidelines

### System Prompt Strategy

The system prompt defines the chatbot's behavior:

```
"You are a helpful payment system assistant with access to bills and payments data."
```

**Key instructions in prompt**:
1. Role definition (what the assistant is)
2. Capabilities (what it can do)
3. Constraints (what it cannot do)
4. Output format (how to structure responses)
5. Data context (what data is available)

### Few-Shot Learning (Optional)

Add examples in the prompt for complex queries:

```
EXAMPLE 1:
User: "How much am I overdue?"
Context: Bills #1 (OVERDUE, $5000), #2 (PAID)
Response: "You are overdue by $5,000 on Bill #1"

USER QUESTION: {user_question}
CONTEXT: {retrieved_data}
```

### Temperature Control

- `temperature=0.7` (default) - Balanced, natural responses
- `temperature=0.0` - Deterministic, factual
- `temperature=1.0+` - Creative, varied

For financial data, use **0.7** (balanced).

---

## Vector Store Management

### FAISS Index Structure

```
backend/data/
├── faiss_index.bin        # Vector index (binary)
├── faiss_metadata.pkl     # Document metadata (pickle)
```

### Index Operations

**Add documents**:
```python
from app.services.vector_store_service import vector_store
vector_store.add_documents(embeddings, documents)
```

**Search documents**:
```python
results = vector_store.search(query_embedding, k=5)
```

**Get stats**:
```python
stats = vector_store.get_stats()
# Returns: total_documents, embedding_dimension, index_size_mb
```

**Clear index**:
```python
vector_store.delete_all()
```

---

## Performance & Costs

### Embedding Generation
- Model: `all-MiniLM-L6-v2` (384 dims, local)
- Cost: FREE (runs locally)
- Speed: ~1000 docs/second
- Memory: ~200MB for 1000 docs

### LLM Queries
- Model: `gpt-3.5-turbo`
- Cost: $0.0005 per 1K input tokens, $0.0015 per 1K output tokens
- Typical query: 150-300 tokens = $0.0002-$0.0005
- Speed: 1-3 seconds per query

### Monthly Estimate (100 queries)
- Embeddings: FREE (one-time per FY)
- Queries: 100 × $0.0003 = $0.03
- **Total: ~$0.03/month**

### Vector Store Storage
- FAISS index: ~1MB per 1000 docs
- Metadata: ~50KB per 1000 docs
- 1000 bills = ~1.1MB total

---

## Troubleshooting

### "OpenAI API key not found"
- Check `.env` file has `OPENAI_API_KEY`
- Verify key is valid (not expired)
- Restart backend server

### "No bills found for indexing"
- Verify bills exist in MongoDB for that FY
- Check fiscal year name matches exactly
- Call `/api/chatbot/index` endpoint first

### "Slow queries"
- First query is slower (model loading)
- Subsequent queries should be <3 seconds
- Increase `RAG_TOP_K` for better accuracy but slower

### "CORS errors"
- Frontend and backend must be on CORS whitelist
- Backend already allows all origins by default
- Check browser console for exact error

### "Vector index corrupted"
- Delete `backend/data/faiss_*.bin` files
- Call `/api/chatbot/rebuild-index` to recreate

---

## Security Considerations

1. **API Key Security**:
   - Never commit `.env` to git
   - Rotate keys periodically
   - Use minimal permission keys

2. **Data Isolation**:
   - Each query filters by `X-Fiscal-Year` header
   - Vector store includes FY in metadata
   - Users see only their FY data

3. **Rate Limiting** (Optional):
   - Add rate limiter to prevent abuse
   - Recommend: 1 query per second per user

4. **Cost Control**:
   - Set OpenAI API usage limits
   - Monitor via OpenAI dashboard
   - Set alerts for unexpected usage

---

## Future Enhancements

1. **Multi-turn Conversations**: Store context between messages
2. **Real-time Data**: Subscribe to bill updates
3. **Custom LLM**: Replace OpenAI with self-hosted Llama
4. **Analytics**: Track popular questions
5. **Caching**: Cache frequent queries to reduce costs
6. **Embeddings Update**: Auto-refresh when bills change
7. **Admin Analytics**: Dashboard of chatbot usage
8. **Export**: Export chat history as PDF

---

## Architecture Diagram

```
User Message
    ↓
[FastAPI Endpoint]
    ↓
[Query Embedding] - sentence-transformers
    ↓
[Vector Search] - FAISS index
    ↓
[MongoDB Retrieval] - Full document data
    ↓
[Prompt Injection] - System prompt + context
    ↓
[LLM Call] - OpenAI gpt-3.5-turbo
    ↓
[Response Formatting]
    ↓
[JSON Response to Frontend]
    ↓
React Chat Component
    ↓
User sees answer
```

