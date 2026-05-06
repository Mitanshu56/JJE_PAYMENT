"""
Embeddings Service - Generates and manages document embeddings
Optimized for invoice/payment RAG search.
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Optional


class EmbeddingsService:
    """Generate embeddings for bills, payments, and statement documents."""

    def __init__(self):
        self.model = None
        self.embedding_dim = 384
        self.model_name = "all-MiniLM-L6-v2"

    def _get_model(self):
        """Lazy-load SentenceTransformer model only when needed."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        return self.model

    def encode_text(self, text: str) -> np.ndarray:
        """Convert single text into embedding vector."""
        if not text or not text.strip():
            text = "empty document"

        model = self._get_model()
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding.astype(np.float32)

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode multiple texts efficiently."""
        safe_texts = [
            text if text and text.strip() else "empty document"
            for text in texts
        ]

        model = self._get_model()
        embeddings = model.encode(
            safe_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.astype(np.float32)

    def normalize_party_name(self, name: Optional[str]) -> str:
        """
        Normalize party/client name for better matching.
        Example:
        'Enviro Control Private LTD' -> 'enviro control'
        """
        if not name:
            return ""

        name = name.lower().strip()
        
        # Remove common company suffixes BEFORE removing punctuation (so patterns match)
        # Order matters: longer patterns first
        suffixes = [
            (r'\bprivate\s+limited\b', ''),     # "private limited" -> ""
            (r'\bpvt\s+ltd\b', ''),              # "pvt ltd" -> ""
            (r'\bpvt\.\s+ltd\.\b', ''),          # "pvt. ltd." -> ""
            (r'\bpvt\.\s*ltd\b', ''),            # "pvt. ltd" -> ""
            (r'\bpvt\s+limited\b', ''),          # "pvt limited" -> ""
            (r'\bprivate\b', ''),                # "private" -> ""
            (r'\blimited\b', ''),                # "limited" -> ""
            (r'\bpvt\b', ''),                    # "pvt" -> ""
            (r'\bltd\b', ''),                    # "ltd" -> ""
            (r'\bltd\.\b', ''),                  # "ltd." -> ""
            (r'\bllp\b', ''),                    # "llp" -> ""
            (r'\binc\b', ''),                    # "inc" -> ""
            (r'\binc\.\b', ''),                  # "inc." -> ""
            (r'\bcorporation\b', ''),            # "corporation" -> ""
            (r'\bcorp\b', ''),                   # "corp" -> ""
            (r'\bco\b', ''),                     # "co" -> ""
            (r'\bco\.\b', ''),                   # "co." -> ""
        ]
        
        for pattern, replacement in suffixes:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        # Remove all punctuation and normalize spaces
        name = re.sub(r'[^a-z0-9\s]', '', name)
        
        # Collapse multiple spaces and trim
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name

    def prepare_documents(self, records: List[Dict]) -> Tuple[List[str], np.ndarray]:
        """
        Prepare MongoDB bills/payments/statements for embedding.
        One record = one searchable document.
        """
        doc_texts = [self._create_document_text(record) for record in records]

        if not doc_texts:
            return [], np.empty((0, self.embedding_dim), dtype=np.float32)

        embeddings = self.encode_batch(doc_texts)
        return doc_texts, embeddings

    def _money(self, value) -> str:
        """Safely format amount values."""
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return "0.00"

    def _create_document_text(self, record: Dict) -> str:
        """
        Create searchable text representation using your actual schema.

        Supports:
        - bills
        - payments
        - statement_entries
        """

        document_type = (record.get("document_type") or record.get("source") or "bill").lower()

        # Common fields
        fiscal_year = record.get("fiscal_year", "N/A")
        party_name = record.get("party_name", "N/A")
        party_name_norm = self.normalize_party_name(party_name)

        # Bill/invoice fields from the current schema
        invoice_no = record.get("invoice_no") or record.get("invoice_number") or record.get("bill_no") or "N/A"
        invoice_date = record.get("invoice_date") or record.get("date") or record.get("bill_date") or "N/A"
        grand_total = record.get("grand_total") or 0
        paid_amount = record.get("paid_amount") or 0
        remaining_amount = record.get("remaining_amount") or 0
        status = record.get("status") or "N/A"
        gst_value = record.get("gst") or record.get("gst_amount") or record.get("total_gst") or 0
        cgst = record.get("cgst") or 0
        sgst = record.get("sgst") or 0
        igst = record.get("igst") or 0

        # Payment fields
        payment_id = record.get("payment_id") or "N/A"
        payment_date = record.get("payment_date") or "N/A"
        payment_amount = record.get("amount") or 0
        reference = record.get("reference") or "N/A"

        # Statement fields
        value_date = record.get("value_date") or "N/A"
        deposit = record.get("deposit") or 0
        narration = record.get("narration") or ""

        if document_type in ["payment", "payments"]:
            return f"""
Document Type: Payment
Payment ID: {payment_id}
Payment Date: {payment_date}
Party Name: {party_name}
Normalized Party Name: {party_name_norm}
Amount Paid: {self._money(payment_amount)}
Reference: {reference}
Fiscal Year: {fiscal_year}
""".strip()

        if document_type in ["statement", "statement_entries", "bank_statement"]:
            return f"""
Document Type: Bank Statement Entry
Value Date: {value_date}
Deposit Amount: {self._money(deposit)}
Narration: {narration}
Reference: {reference}
Fiscal Year: {fiscal_year}
""".strip()

        return f"""
Document Type: Bill / Invoice
Invoice Number: {invoice_no}
Invoice Date: {invoice_date}
Party Name: {party_name}
Normalized Party Name: {party_name_norm}
Grand Total: {self._money(grand_total)}
Paid Amount: {self._money(paid_amount)}
Remaining Amount: {self._money(remaining_amount)}
Status: {status}
    GST Value: {self._money(gst_value)}
    CGST: {self._money(cgst)}
    SGST: {self._money(sgst)}
    IGST: {self._money(igst)}
Fiscal Year: {fiscal_year}

Search Keywords:
client {party_name}
party {party_name}
invoice {invoice_no}
pending amount {self._money(remaining_amount)}
paid amount {self._money(paid_amount)}
total amount {self._money(grand_total)}
    gst {self._money(gst_value)}
""".strip()


# Singleton instance
embeddings_service = EmbeddingsService()


def normalize_party_name(name: Optional[str]) -> str:
    """Module-level normalize function (convenience wrapper)."""
    return embeddings_service.normalize_party_name(name)
