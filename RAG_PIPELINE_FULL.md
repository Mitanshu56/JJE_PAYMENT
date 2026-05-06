**RAG Pipeline — Full Project Reference

Overview
- **Purpose**: This document describes how the Retrieval-Augmented Generation (RAG) pipeline is implemented in this project, what each component does, and how to prompt the system for accurate, deterministic reporting answers (counts, totals, pending amounts, payment history, statement summaries).
- **Scope**: Backend (FastAPI + MongoDB + Motor), Embeddings (sentence-transformers), Vector Store (FAISS), RAG orchestration (rag_service), deterministic DB-first routing (chatbot_routes), and Frontend chat UI.

**Architecture**
- **Backend**: FastAPI app at `backend/app` exposes endpoints under `/api/chatbot/*` and other resources. Database access uses Motor (`AsyncIOMotorDatabase`). See [backend/app/routes/chatbot_routes.py](backend/app/routes/chatbot_routes.py#L1).
- **Database**: MongoDB collections used:
  - `bills` — documents with fields: `invoice_no`, `party_name`, `invoice_date`, `grand_total`, `paid_amount`, `remaining_amount`, `status`, `fiscal_year`.
  - `payments` — `payment_id`, `payment_date`, `party_name`, `amount`, `reference`, `fiscal_year`.
  - `statement_entries` — `value_date`, `deposit`, `narration`, `reference`, `fiscal_year`.
  - `fiscal_years` — fiscal year metadata (stored under `value`, `name`, or `label`).
- **Embeddings**: `backend/app/services/embeddings_service.py` (lazy-loads `SentenceTransformer('all-MiniLM-L6-v2')`) to avoid import-time failures.
- **Vector Store**: `backend/app/services/vector_store_service.py` uses FAISS `IndexFlatL2` (dimension 384) and stores metadata alongside vectors for filtering by `fiscal_year` and other fields.
- **RAG orchestration**: `backend/app/services/rag_service.py` builds searchable documents, calls embeddings, stores vectors, performs nearest-neighbor search (filtered by metadata), constructs LLM prompts, and calls the LLM client (Groq/OpenRouter/OpenAI/Deepseek depending on config).
- **Chat routing**: `backend/app/routes/chatbot_routes.py` implements DB-first deterministic handlers for structured operational queries (counts, totals, pending amounts, payment history, statements). If the DB-first path cannot answer, it falls back to the RAG pipeline.

**Data Flow**
1. Indexing: bills/payments are fetched for a `fiscal_year` and passed to `rag_service.index_bills_and_payments()` which:
   - Converts each document to a textual chunk with metadata (invoice_no, party_name, dates, amounts, fiscal_year).
   - Creates embeddings in batches and writes vectors + metadata to FAISS + local metadata store.
2. Querying (chat): `/api/chatbot/chat` receives user message and current `fiscal_year`.
   - DB-first path: `_query_database_answer()` examines the message for structured intent (counts, pending, payments, statements). If matched, it runs Mongo queries (safe fetch + sum) against `bills`, `payments`, or `statement_entries` and returns deterministic results.
   - RAG fallback: if DB-first returns None, `rag_service.chat()` embeds the query, searches FAISS with `top_k` (and metadata filters e.g., `fiscal_year`), composes an LLM prompt with retrieved contexts, then calls the LLM to generate the response.

**Fiscal Year Handling**
- Fiscal years use an April-to-March convention. Fiscal labels are `FY-YYYY-YYYY` (e.g., `FY-2025-2026`).
- User month-only queries like "May 2025" are resolved to a calendar year inside the selected fiscal year via `_year_for_month_in_fiscal_year()`.
- Fiscal year documents may store label under `value`, `name`, or `label` — indexing & lookup code checks all three.

**Deterministic DB-first Routing (why and how)**
- Why: Reporting queries require exact counts and sums; an LLM hallucinating numbers is unacceptable for this product.
- How: `chatbot_routes._query_database_answer()` contains detectors: `_is_invoice_count_query()`, `_is_pending_amount_query()`, `_is_payment_history_query()`, `_is_statement_query()` and extracts `party_name` and `month/year`.
- Behavior:
  - If the message contains a party name and a count intent, it constructs a precise MongoDB filter and counts or aggregates documents.
  - If count == 0 but the client exists in other fiscal years, a new relaxed fallback `_relaxed_party_search()` runs to find matches across fiscal years and returns a helpful diagnostic message.

**Prompts and Prompting Guidance**
- **System prompt (RAG)**: Keep system prompt deterministic and instruct LLM to only use provided context for facts and label the source. Example:
  - "You are an assistant that answers accounting queries based only on the provided documents. If asked for counts or totals, compute them from provided facts; if uncertain, say you cannot confirm and provide the database summary." 
- **User prompt templates (RAG)**:
  - Short operational query: "How many invoices do I have for Enviro Control Private LTD this fiscal year?"
  - Date-scoped: "Total pending amount for Enviro Control Private LTD in May 2025"
  - Statement-scope: "Show bank statement deposits for May 2025"
- **Local DB-first examples (expected deterministic responses)**:
  - Input: "how many number of bills i have of client name Enviro Control Private LTD"
    - DB response (if fiscal-year selected and has 58 invoices): "You have 58 invoice(s) for Enviro Control Private LTD in the selected fiscal year." (source: database)
  - Input: "what is the pending amount for Enviro Control Private LTD"
    - DB response: "Your total pending amount for Enviro Control Private LTD in the selected fiscal year is $12,345.67." (computed from `remaining_amount` for PENDING statuses)
- **RAG fallback example**:
  - If DB-first can't answer (open-ended / extraction needed), the RAG prompt should include a short context block of top-K retrieved documents, each prefixed with its source metadata (invoice_no, date, fiscal_year). Ask the LLM to synthesize and cite source lines.

**Embedding & Retrieval Best Practices (for efficiency & accuracy)**
- Use smaller, fast embedding models (all-MiniLM-L6-v2) for CPU-friendly embedding; lazy-load heavy dependencies to avoid startup failures.
- Create metadata fields for every vector: `fiscal_year`, `invoice_no`, `party_name`, `document_type` to enable strict metadata filtering before nearest-neighbor search.
- Use FAISS with `IndexFlatL2` for small-to-medium datasets and consider IVF/OPQ for larger corpora.
- Batch embedding creation and avoid per-document calls; use encode_batch() in `embeddings_service`.
- Keep the retrieval `top_k` small (e.g., 5–10) and prefer reranking (e.g., token-level or cross-encoder) before constructing the final prompt.
- Cache recent query embeddings and search results when identical queries are common.

**Prompt / LLM Efficiency**
- Trim context: only include the most relevant fields and a short excerpt of the invoice/statement when constructing context.
- Use explicit instructions: "Only use the following documents to compute numeric answers. If the documents are insufficient, say 'I can't confirm'."
- For numeric aggregations prefer DB-first; avoid relying on LLM to sum many entries.

**Error Modes & Troubleshooting**
- Common mismatch: party name exact-match vs stored variants (extra whitespace, suffixes). Mitigations:
  - Use a relaxed substring search (`_relaxed_party_search`) and return per-fiscal-year counts for diagnosis.
  - Add normalized party_name canonicalization at ingestion (lowercase, trim punctuation) and store a `party_name_norm` field.
- Fiscal-year mismatch: ensure fiscal lookup checks `value`, `name`, and `label`.
- Import-time ML library failures: lazy-load `SentenceTransformer` inside the embedding getter.
- Index empty: verify `index_data` endpoint uses the same fiscal-year selection logic and that bills have valid `invoice_date` and `fiscal_year`.

**Operational / Dev Notes**
- Files of interest:
  - [backend/app/routes/chatbot_routes.py](backend/app/routes/chatbot_routes.py#L1) — DB-first routing, detectors, and chat endpoint.
  - [backend/app/services/embeddings_service.py](backend/app/services/embeddings_service.py#L1) — embedding creation (lazy-load model).
  - [backend/app/services/vector_store_service.py](backend/app/services/vector_store_service.py#L1) — FAISS index and metadata handling.
  - [backend/app/services/rag_service.py](backend/app/services/rag_service.py#L1) — RAG orchestration and LLM client management.
- Environment: Windows development; run FastAPI from `backend` with the venv python. Ensure MongoDB is reachable and `fiscal_years` documents exist.

**How to improve model efficiency & correctness (actionable steps)**
- Keep deterministic DB-first answers for any count/total/statement queries.
- Add a `party_name_norm` on ingest (lowercase, stripped punctuation) and match against it for deterministic filters.
- Precompute per-client, per-fiscal-year aggregates at ingest or via nightly batch jobs to answer counts instantly.
- Use hybrid retrieval: metadata filter -> ANN search -> cross-encoder rerank.
- Monitor and log which branch handled each chat (DB-first vs RAG) so queries that go to RAG can be analyzed and new DB-first detectors created.

**Sample prompts to pass to GPT for improving the system**
- "Given the project's code (embedding, vector store, DB-first handlers) suggest 5 concrete ways to reduce RAG cost while maintaining accuracy for financial queries. Prioritize changes that are easy to implement."
- "Propose a party-name canonicalization and fuzzy matching algorithm (Python) that minimizes false positives when matching `party_name` in `bills` documents. Provide code snippets suitable for our project." 

**Next steps & Checklist**
- [ ] Run the new relaxed-search flow and verify responses for a known client (e.g., Enviro Control Private LTD).
- [ ] Add `party_name_norm` during ingestion and migrate existing `bills` documents.
- [ ] Instrument chat logs to record which resolution path (DB-first vs RAG) produced each answer.
- [ ] Add unit tests for `_extract_party_name()`, fiscal-year mappings, and DB-first queries.

Appendix — Example Q/A that should be deterministic
- Q: "how many number of bills i have of client name Enviro Control Private LTD"
  - Expected (DB-first): "You have 58 invoice(s) for Enviro Control Private LTD in the selected fiscal year." (source: database)
- Q: "what is the pending amount for Enviro Control Private LTD"
  - Expected (DB-first): "Your total pending amount for Enviro Control Private LTD in the selected fiscal year is $X,XXX.XX." (computed from `remaining_amount` for statuses in pending set)

Contact
- If you want, I can now run a quick verification query against your running backend and DB to validate the report for "Enviro Control Private LTD" and adjust detection rules if needed.
