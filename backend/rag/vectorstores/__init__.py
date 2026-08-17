"""Vector store adapters."""

from backend.rag.vectorstores.faiss_store import LocalFaissVectorStore
from backend.rag.vectorstores.protocols import VectorRecord, VectorSearchResult, VectorStore
from backend.rag.vectorstores.qdrant import QdrantVectorStore
from backend.rag.vectorstores.registry import VectorStoreRegistry

__all__ = [
    "LocalFaissVectorStore",
    "QdrantVectorStore",
    "VectorRecord",
    "VectorSearchResult",
    "VectorStore",
    "VectorStoreRegistry",
]
