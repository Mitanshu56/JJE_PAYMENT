"""
Vector Store Service - Manages FAISS vector index for fast similarity search
"""
from __future__ import annotations

try:
    import faiss
except Exception:
    faiss = None
import numpy as np
from typing import List, Dict, Tuple
import os
import pickle
from collections import Counter


class _FallbackIndex:
    """Small in-memory cosine-similarity index used when FAISS is unavailable."""

    def __init__(self, embedding_dim: int):
        self.d = embedding_dim
        self._vectors = np.empty((0, embedding_dim), dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return int(self._vectors.shape[0])

    def add(self, embeddings: np.ndarray):
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        self._vectors = np.vstack([self._vectors, embeddings.astype(np.float32)]) if self._vectors.size else embeddings.astype(np.float32)

    def search(self, query: np.ndarray, k: int):
        if self._vectors.size == 0:
            distances = np.full((1, k), -1.0, dtype=np.float32)
            indices = np.full((1, k), -1, dtype=np.int64)
            return distances, indices

        scores = np.dot(self._vectors, query[0])
        order = np.argsort(-scores)[:k]
        distances = np.full((1, k), -1.0, dtype=np.float32)
        indices = np.full((1, k), -1, dtype=np.int64)
        distances[0, : len(order)] = scores[order]
        indices[0, : len(order)] = order
        return distances, indices

    def reset(self):
        self._vectors = np.empty((0, self.d), dtype=np.float32)

    @property
    def metric_type(self):
        return 0

class VectorStoreService:
    """Manages FAISS vector index for bill/payment retrieval using inner-product (cosine on normalized embeddings)."""
    
    def __init__(self, embedding_dim: int = 384, index_path: str = None):
        self.embedding_dim = embedding_dim
        self.index_path = index_path or 'backend/data/faiss_index.bin'
        self.metadata_path = self.index_path.replace('.bin', '_metadata.pkl')

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # Load or create an IndexFlatIP for cosine/inner-product searches (embeddings should be normalized)
        self.index = self._load_or_create_index()
        self.metadata = self._load_metadata()
        self.doc_count = len(self.metadata)

    def _load_or_create_index(self):
        """Load existing FAISS index if compatible, otherwise create a new IndexFlatIP."""
        if faiss is None:
            print(f"FAISS is unavailable, using in-memory fallback index with dimension {self.embedding_dim}")
            return _FallbackIndex(self.embedding_dim)

        try:
            if os.path.exists(self.index_path):
                index = faiss.read_index(self.index_path)
                # Basic compatibility checks
                existing_dim = getattr(index, 'd', None)
                is_ip = index.__class__.__name__ == 'IndexFlatIP' or getattr(index, 'metric_type', None) == faiss.METRIC_INNER_PRODUCT
                if existing_dim == self.embedding_dim and is_ip:
                    print(f"Loaded FAISS IndexFlatIP with {index.ntotal} vectors")
                    return index
                else:
                    print("Existing index incompatible (dimension/type mismatch). Recreating new IndexFlatIP.")
                    # Attempt to remove old files and start fresh
                    try:
                        os.remove(self.index_path)
                    except Exception:
                        pass
                    try:
                        os.remove(self.metadata_path)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Could not load index: {e}")

        print(f"Creating new FAISS IndexFlatIP with dimension {self.embedding_dim}")
        return faiss.IndexFlatIP(self.embedding_dim)

    def _load_metadata(self) -> List[Dict]:
        """Load document metadata safely."""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Could not load metadata: {e}")
        return []

    def add_documents(self, embeddings: np.ndarray, documents: List[Dict]):
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"Embedding dimension mismatch: {embeddings.shape[1]} != {self.embedding_dim}")

        stored_documents = []
        for embedding, document in zip(embeddings, documents):
            stored_document = document.copy()
            stored_document['_embedding'] = np.asarray(embedding, dtype=np.float32).tolist()
            stored_documents.append(stored_document)

        # Add vectors and metadata
        try:
            self.index.add(embeddings.astype(np.float32))
        except Exception as e:
            # If add fails, try recreating index and re-adding
            print(f"FAISS add failed: {e}. Recreating index and clearing metadata.")
            self.index = _FallbackIndex(self.embedding_dim) if faiss is None else faiss.IndexFlatIP(self.embedding_dim)
            self.index.add(embeddings.astype(np.float32))
            self.metadata = []

        # Store metadata
        self.metadata.extend(stored_documents)
        self.doc_count = len(self.metadata)

        # Persist
        self._save_index()
        self._save_metadata()
        print(f"Added {len(documents)} documents. Total: {self.doc_count}")

    def search(self, query_embedding: np.ndarray, k: int = 5, filters: Dict = None) -> List[Dict]:
        """Search for similar documents with optional metadata filtering.

        Filters are matched by exact equality against metadata keys.
        """
        if self.doc_count == 0:
            return []

        q = query_embedding.reshape(1, -1).astype(np.float32)
        # perform search for a larger window to allow filtering out non-matching metadata
        fetch_k = min(max(50, k * 5), max(5, self.doc_count))
        distances, indices = self.index.search(q, fetch_k)

        results = []
        seen = set()
        for idx, score in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[int(idx)]
            # apply filters if provided
            if filters:
                ok = True
                for fk, fv in filters.items():
                    if meta.get(fk) != fv:
                        ok = False
                        break
                if not ok:
                    continue
            if int(idx) in seen:
                continue
            seen.add(int(idx))
            doc = meta.copy()
            doc.pop('_embedding', None)
            # For IndexFlatIP with normalized embeddings, score is cosine similarity
            similarity = float(score)
            doc['similarity_score'] = similarity
            results.append(doc)
            if len(results) >= k:
                break

        return results

    def replace_documents_for_fiscal_year(self, fiscal_year: str, embeddings: np.ndarray, documents: List[Dict]):
        """Replace all documents for one fiscal year while preserving other years when possible."""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"Embedding dimension mismatch: {embeddings.shape[1]} != {self.embedding_dim}")

        stored_documents = []
        for embedding, document in zip(embeddings, documents):
            stored_document = document.copy()
            stored_document['fiscal_year'] = stored_document.get('fiscal_year') or fiscal_year
            stored_document['_embedding'] = np.asarray(embedding, dtype=np.float32).tolist()
            stored_documents.append(stored_document)

        remaining_docs = [doc for doc in self.metadata if doc.get('fiscal_year') != fiscal_year]
        replaced_count = len(self.metadata) - len(remaining_docs)
        can_rebuild_remaining = all(doc.get('_embedding') is not None for doc in remaining_docs)

        if can_rebuild_remaining:
            rebuilt_docs = remaining_docs + stored_documents
            rebuilt_embeddings = []
            for doc in rebuilt_docs:
                emb = doc.get('_embedding')
                if emb is None:
                    continue
                rebuilt_embeddings.append(np.asarray(emb, dtype=np.float32))

            self.index = _FallbackIndex(self.embedding_dim) if faiss is None else faiss.IndexFlatIP(self.embedding_dim)
            if rebuilt_embeddings:
                self.index.add(np.vstack(rebuilt_embeddings).astype(np.float32))
            self.metadata = rebuilt_docs
            self.doc_count = len(self.metadata)
            self._save_index()
            self._save_metadata()
            return {
                'mode': 'rebuild',
                'replaced_count': replaced_count,
                'added_count': len(stored_documents),
                'total_documents': self.doc_count,
            }

        # Fallback: rebuild only the selected fiscal year and replace the existing index.
        self.index = _FallbackIndex(self.embedding_dim) if faiss is None else faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = stored_documents
        self.index.add(embeddings.astype(np.float32))
        self.doc_count = len(stored_documents)
        self._save_index()
        self._save_metadata()
        return {
            'mode': 'full_reset',
            'replaced_count': replaced_count,
            'added_count': len(stored_documents),
            'total_documents': self.doc_count,
        }

    def delete_all(self):
        try:
            self.index.reset()
        except Exception:
            self.index = _FallbackIndex(self.embedding_dim) if faiss is None else faiss.IndexFlatIP(self.embedding_dim)
        self.metadata.clear()
        self.doc_count = 0
        self._save_index()
        self._save_metadata()
        print("Index cleared")

    def _save_index(self):
        try:
            if faiss is None:
                return
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            print(f"Error saving index: {e}")

    def _save_metadata(self):
        try:
            os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def get_stats(self) -> Dict:
        return {
            "total_documents": self.doc_count,
            "embedding_dimension": self.embedding_dim,
            "index_size_mb": os.path.getsize(self.index_path) / 1024 / 1024 if os.path.exists(self.index_path) else 0
        }

    def get_index_summary(self, fiscal_year: str | None = None) -> Dict:
        """Return document totals broken down by document type and fiscal year."""
        docs = self.metadata
        if fiscal_year:
            docs = [doc for doc in docs if doc.get('fiscal_year') == fiscal_year]

        type_counts = Counter((doc.get('document_type') or 'unknown') for doc in docs)
        fiscal_year_counts = Counter((doc.get('fiscal_year') or 'unknown') for doc in self.metadata)

        return {
            'total_indexed_documents': len(docs),
            'document_type_breakdown': dict(type_counts),
            'fiscal_year_breakdown': dict(fiscal_year_counts),
        }

    def get_breakdown_by_document_type(self, fiscal_year: str | None = None) -> Dict[str, int]:
        """Compatibility helper returning only the document type breakdown."""
        return self.get_index_summary(fiscal_year=fiscal_year).get('document_type_breakdown', {})

    def get_breakdown_by_fiscal_year(self) -> Dict[str, int]:
        """Compatibility helper returning the fiscal year breakdown."""
        return self.get_index_summary().get('fiscal_year_breakdown', {})

    def get_sample_metadata(self, limit: int = 3, fiscal_year: str | None = None) -> List[Dict]:
        """Return a small sample of indexed metadata for debugging and index status APIs."""
        docs = self.metadata
        if fiscal_year:
            docs = [doc for doc in docs if doc.get('fiscal_year') == fiscal_year]
        sample = []
        for doc in docs[:limit]:
            item = doc.copy()
            item.pop('_embedding', None)
            sample.append(item)
        return sample
    
    def delete_all(self):
        """Clear the index and metadata"""
        self.index.reset()
        self.metadata.clear()
        self.doc_count = 0
        self._save_index()
        self._save_metadata()
        print("Index cleared")
    
    def _save_index(self):
        """Save FAISS index to disk"""
        try:
            if faiss is None:
                return
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk"""
        try:
            os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        return {
            "total_documents": self.doc_count,
            "embedding_dimension": self.embedding_dim,
            "index_size_mb": os.path.getsize(self.index_path) / 1024 / 1024 if os.path.exists(self.index_path) else 0
        }


# Singleton instance
vector_store = VectorStoreService()
