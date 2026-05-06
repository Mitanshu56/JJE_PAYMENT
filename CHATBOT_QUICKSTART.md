# RAG Chatbot Quick Start

## 5-Minute Setup

### Step 1: Get OpenAI API Key (2 min)
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key

### Step 2: Update Environment (1 min)
Edit `backend/.env`:
```env
OPENAI_API_KEY=sk-your-key-here
```

### Step 3: Install & Run (2 min)

**Terminal 1 - Backend**:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

**Terminal 3 - Test (Optional)**:
```bash
curl -X POST http://localhost:8000/api/chatbot/index \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"fiscal_year": "FY-2025-2026"}'
```

---

## Testing Checklist

### ✅ Backend Running
```bash
curl http://localhost:8000/api/health
# Should return: {"status": "ok"}
```

### ✅ Frontend Running
- Open http://localhost:5173 in browser
- Login with admin credentials

### ✅ Chatbot Widget Visible
- Should see blue chat button in bottom-right corner

### ✅ Index Data
- Click chat button
- Chat window auto-indexes on first open
- Look for: "Data indexed successfully"

### ✅ Send Test Message
- Type: "Show me my bills"
- Should get response with bill information

---

## Test Queries

```
1. "What's in my fiscal year?"
2. "How many bills do I have?"
3. "Show overdue bills"
4. "Total amount due?"
5. "When are my bills due?"
```

---

## Files Created/Modified

### New Files:
```
backend/app/services/embeddings_service.py     ← Embeddings generation
backend/app/services/vector_store_service.py   ← FAISS vector DB
backend/app/services/rag_service.py            ← RAG orchestration
backend/app/routes/chatbot_routes.py           ← API endpoints
frontend/src/components/ChatBot.jsx            ← React chat UI
RAG_PIPELINE.md                                ← Full documentation
CHATBOT_SETUP.md                               ← Setup guide
```

### Modified Files:
```
backend/requirements.txt                       ← New dependencies added
backend/app/main.py                            ← Chatbot router included
frontend/src/pages/Dashboard.jsx               ← ChatBot component added
```

---

## Data Flow

```
1. User types message in React component
   ↓
2. Sent to POST /api/chatbot/chat endpoint
   ↓
3. Message embedded using sentence-transformers (384 dims)
   ↓
4. Query FAISS index for similar bills (top 5)
   ↓
5. Fetch full bill data from MongoDB
   ↓
6. Build prompt with system role + context + question
   ↓
7. Send to OpenAI gpt-3.5-turbo
   ↓
8. Return response to frontend
   ↓
9. Display in chat bubble with context summary
```

---

## Monitoring

### Check Indexing Status
```bash
curl http://localhost:8000/api/chatbot/status \
  -H "Authorization: Bearer token"
```

### View Conversation History
```bash
curl http://localhost:8000/api/chatbot/history \
  -H "Authorization: Bearer token"
```

### Monitor OpenAI Usage
1. Go to https://platform.openai.com/account/billing/overview
2. Check "Usage this month"
3. Set usage limits if needed

---

## Common Issues

| Issue | Solution |
|-------|----------|
| "API key not valid" | Check key starts with `sk-` in .env |
| "No bills indexed" | Call `/api/chatbot/index` endpoint first |
| "Chat window not showing" | Check browser console for errors |
| "Slow responses" | First query loads model (slow), then fast |
| "No response" | Check OpenAI API key is valid |

---

## Next Steps

1. **Customize system prompt**: Edit `SYSTEM_PROMPT` in `rag_service.py`
2. **Add more context**: Modify `_build_context()` method
3. **Tune performance**: Adjust `RAG_TOP_K` and `max_tokens`
4. **Monitor costs**: Set OpenAI usage alerts
5. **Add features**: Multi-turn conversations, export history

---

## Production Checklist

- [ ] Set `DEBUG=False` in .env
- [ ] Enable HTTPS on frontend
- [ ] Set specific CORS origins (not *)
- [ ] Add rate limiting to `/api/chatbot/chat`
- [ ] Enable OpenAI API key rotation
- [ ] Set OpenAI monthly spending limit
- [ ] Monitor vector index size
- [ ] Backup FAISS index files
- [ ] Add error logging/monitoring
- [ ] Test with real user load

