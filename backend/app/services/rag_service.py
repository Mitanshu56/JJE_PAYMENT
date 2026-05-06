"""
RAG Service - Orchestrates retrieval and LLM generation
"""

import os
import traceback
from typing import List, Dict
from datetime import datetime
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
from typing import Any
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except Exception:
    AsyncIOMotorDatabase = Any

from app.services.embeddings_service import embeddings_service
from app.services.vector_store_service import vector_store
from app.core.config import logger, settings


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
_llm_client = None


def get_llm_client():
    """Lazily create and return an OpenAI-compatible client."""
    global _llm_client

    if OpenAI is None:
        raise RuntimeError("OpenAI client library is not available in this environment")

    if _llm_client is not None:
        return _llm_client

    provider = (settings.LLM_PROVIDER or LLM_PROVIDER).lower()

    if provider == "deepseek":
        _llm_client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE or "https://api.deepseek.com",
        )

    elif provider == "openrouter":
        _llm_client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_API_BASE or "https://api.openrouter.ai/v1",
        )

    elif provider == "groq":
        _llm_client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE or "https://api.groq.com/openai/v1",
        )

    else:
        _llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    return _llm_client


SYSTEM_PROMPT = """
You are a strict accounting assistant for a payment tracking system.

Rules:
1. Answer only using the provided context.
2. Do not guess, estimate, or invent amounts, invoice numbers, dates, or client names.
3. For exact financial values like pending amount, paid amount, invoice count, total amount, due amount, payment history, or invoice status, prefer database results.
4. If database result is not provided, say: "I cannot confirm this from the available data."
5. Never perform large numeric aggregation from retrieved chunks unless explicitly provided as a database summary.
6. Always mention the source as either database or retrieved documents.
7. Be concise, clear, and professional.
"""


class RAGService:
    """Manages the complete RAG pipeline."""

    def __init__(self, model: str = None, max_context_tokens: int = 2000):
        self.model = model or LLM_MODEL or "llama-3.1-8b-instant"
        self.max_context_tokens = max_context_tokens
        self.conversation_history = []

    def _safe_float(self, value) -> float:
        """Safely convert any value to float."""
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _safe_money(self, value) -> str:
        """Safely format money values."""
        return f"{self._safe_float(value):,.2f}"

    def _get_amount_value(self, doc: Dict):
        """Get best available amount field from different schemas."""
        return (
            doc.get("amount")
            or doc.get("grand_total")
            or doc.get("remaining_amount")
            or doc.get("paid_amount")
            or doc.get("deposit")
            or 0
        )

    def _build_index_documents(self, records: List[Dict], fiscal_year: str) -> tuple[List[str], List[Dict], object]:
        """Prepare searchable texts, metadata documents, and embeddings for indexing."""
        normalized_records = []
        for record in records:
            item = dict(record)
            item["fiscal_year"] = item.get("fiscal_year") or fiscal_year
            item["document_type"] = item.get("document_type") or item.get("source") or "bill"
            normalized_records.append(item)

        doc_texts, embeddings = embeddings_service.prepare_documents(normalized_records)
        documents = []

        for i, record in enumerate(normalized_records):
            doc = {
                "doc_id": f"doc_{record.get('_id', i)}",
                "content": doc_texts[i],
                "source": record.get("source") or record.get("document_type") or "bill",
                "document_type": record.get("document_type") or "bill",
                "invoice_no": record.get("invoice_no") or record.get("invoice_number") or record.get("bill_no"),
                "party_name": record.get("party_name"),
                "party_name_norm": embeddings_service.normalize_party_name(record.get("party_name")),
                "invoice_date": record.get("invoice_date") or record.get("date") or record.get("bill_date"),
                "grand_total": record.get("grand_total"),
                "paid_amount": record.get("paid_amount"),
                "remaining_amount": record.get("remaining_amount") or record.get("remaining"),
                "status": record.get("status"),
                "fiscal_year": record.get("fiscal_year") or fiscal_year,
                "payment_id": record.get("payment_id"),
                "payment_date": record.get("payment_date"),
                "amount": record.get("amount") or record.get("grand_total") or record.get("deposit"),
                "reference": record.get("reference"),
                "value_date": record.get("value_date"),
                "deposit": record.get("deposit"),
                "narration": record.get("narration"),
                "embedding_index": i,
            }
            documents.append(doc)

        return doc_texts, documents, embeddings

    async def index_bills_and_payments(self, bills: List[Dict], fiscal_year: str) -> Dict:
        """
        Index bills/payments data for retrieval.
        """

        if not bills:
            return {
                "status": "no_data",
                "count": 0,
            }

        for bill in bills:
            bill["fiscal_year"] = fiscal_year
            bill.setdefault("document_type", "bill")

        doc_texts, documents, embeddings = self._build_index_documents(bills, fiscal_year)

        vector_store.add_documents(embeddings, documents)

        return {
            "status": "success",
            "count": len(bills),
            "fiscal_year": fiscal_year,
            "index_stats": vector_store.get_stats(),
        }

    async def chat(self, user_message: str, fiscal_year: str, top_k: int = 5) -> Dict:
        """
        Process user message with RAG.

        Exact numeric financial queries should be handled in chatbot_routes.py
        before reaching this function.
        """

        try:
            query_embedding = embeddings_service.encode_text(user_message)

            # New vector_store may support filters. Old one may not.
            try:
                retrieved_docs = vector_store.search(
                    query_embedding,
                    k=top_k,
                    filters={"fiscal_year": fiscal_year},
                )
            except TypeError:
                retrieved_docs = vector_store.search(query_embedding, k=top_k)

            # Extra safety filter by FY
            relevant_docs = [
                doc for doc in retrieved_docs
                if doc.get("fiscal_year") == fiscal_year
            ]

            if not relevant_docs:
                relevant_docs = retrieved_docs[:top_k]

            context = self._build_context(relevant_docs)

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"""
FISCAL YEAR:
{fiscal_year}

RETRIEVED CONTEXT:
{context}

USER QUESTION:
{user_message}
""".strip(),
                },
            ]

            client = get_llm_client()

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=700,
                top_p=0.1,
            )

            assistant_message = response.choices[0].message.content
            if assistant_message and 'source:' not in assistant_message.lower():
                assistant_message = f"{assistant_message.strip()}\n\nSource: retrieved documents"

            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
            })

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "status": "success",
                "response": assistant_message,
                "context_docs_count": len(relevant_docs),
                "context_summary": self._summarize_context(relevant_docs),
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "source": "retrieved documents",
            }

        except Exception as e:
            logger.exception("RAG chat generation failed")
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "Failed to generate response",
            }

    async def train_fiscal_year(self, db: AsyncIOMotorDatabase, fiscal_year: str) -> Dict:
        """Index all selected fiscal-year source data into FAISS for RAG use."""
        logger.info("Training started for fiscal_year=%s", fiscal_year)

        bills_query = {"fiscal_year": fiscal_year}
        bills = await db["bills"].find(bills_query).to_list(length=10000)
        payments = await db["payments"].find({"fiscal_year": fiscal_year}).to_list(length=10000)
        statements = await db["statement_entries"].find({"fiscal_year": fiscal_year}).to_list(length=10000)

        logger.info(
            "Records fetched for fiscal_year=%s: bills=%s payments=%s statements=%s",
            fiscal_year,
            len(bills),
            len(payments),
            len(statements),
        )

        records: List[Dict] = []

        for bill in bills:
            item = dict(bill)
            item["document_type"] = "bill"
            records.append(item)

        for payment in payments:
            item = dict(payment)
            item["document_type"] = "payment"
            records.append(item)

        for statement in statements:
            item = dict(statement)
            item["document_type"] = "statement"
            records.append(item)

        if not records:
            logger.info("No records found to train for fiscal_year=%s", fiscal_year)
            return {
                "status": "warning",
                "fiscal_year": fiscal_year,
                "indexed": {"bills": 0, "payments": 0, "statements": 0, "total": 0},
            }

        doc_texts, documents, embeddings = self._build_index_documents(records, fiscal_year)
        logger.info("Embeddings generated for fiscal_year=%s: documents=%s", fiscal_year, len(documents))

        vector_result = vector_store.replace_documents_for_fiscal_year(fiscal_year, embeddings, documents)
        logger.info(
            "FAISS updated for fiscal_year=%s mode=%s total_documents=%s",
            fiscal_year,
            vector_result.get("mode"),
            vector_result.get("total_documents"),
        )
        logger.info("Training completed for fiscal_year=%s", fiscal_year)

        return {
            "status": "success",
            "fiscal_year": fiscal_year,
            "indexed": {
                "bills": len(bills),
                "payments": len(payments),
                "statements": len(statements),
                "total": len(documents),
            },
            "vector_store": vector_result,
        }

    def _build_context(self, documents: List[Dict], max_length: int = 2000) -> str:
        """
        Build safe context string from retrieved documents.
        """

        context_lines = []

        for doc in documents:
            doc_type = doc.get("document_type") or doc.get("source") or "document"

            doc_no = (
                doc.get("invoice_no")
                or doc.get("payment_id")
                or doc.get("reference")
                or "N/A"
            )

            date = (
                doc.get("invoice_date")
                or doc.get("payment_date")
                or doc.get("value_date")
                or "N/A"
            )

            party = doc.get("party_name") or "N/A"
            status = doc.get("status") or "UNKNOWN"
            similarity = self._safe_float(doc.get("similarity_score"))

            line = f"""
Source: retrieved documents
Document Type: {doc_type}
Document No: {doc_no}
Party: {party}
Date: {date}
Status: {status}
Grand Total: ₹{self._safe_money(doc.get("grand_total"))}
Paid Amount: ₹{self._safe_money(doc.get("paid_amount"))}
Remaining Amount: ₹{self._safe_money(doc.get("remaining_amount"))}
Amount: ₹{self._safe_money(doc.get("amount"))}
Deposit: ₹{self._safe_money(doc.get("deposit"))}
Fiscal Year: {doc.get("fiscal_year", "N/A")}
Similarity: {similarity:.3f}
Content:
{doc.get("content", "")}
""".strip()

            context_lines.append(line)

        context = "\n\n---\n\n".join(context_lines)

        if len(context) > max_length:
            context = context[:max_length] + "..."

        return context or "No relevant documents found."

    def _summarize_context(self, documents: List[Dict]) -> Dict:
        """
        Summarize retrieved context safely.
        """

        total_amount = 0.0
        statuses = {}

        for doc in documents:
            amount = self._get_amount_value(doc)
            total_amount += self._safe_float(amount)

            status = doc.get("status") or "UNKNOWN"
            statuses[status] = statuses.get(status, 0) + 1

        avg_similarity = 0.0
        if documents:
            avg_similarity = sum(
                self._safe_float(doc.get("similarity_score"))
                for doc in documents
            ) / len(documents)

        return {
            "total_documents": len(documents),
            "total_amount_from_retrieved_docs": total_amount,
            "status_breakdown": statuses,
            "avg_similarity": avg_similarity,
        }

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()

    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history.copy()


rag_service = RAGService()