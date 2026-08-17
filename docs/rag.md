# RAG

Phase 7 adds local document ingestion and retrieval-augmented generation.

## Flow

1. Upload a file or ingest an allowed local path through the backend.
2. Validate extension, size, root, ignore rules, and binary content.
3. Parse text into sections.
4. Chunk with bounded target and overlap sizes.
5. Embed locally by default.
6. Upsert vectors behind the vector-store adapter.
7. Retrieve relevant chunks, assign `[K#]` citations, and inject them into chat as untrusted context data.

## Supported Inputs

Text, Markdown, HTML, JSON/JSONL, CSV/TSV, common source files, DOCX, and basic PDF text extraction are supported. PDF extraction is best-effort unless `pypdf` is installed.

## Storage

SQLite stores document metadata, chunks, ingestion jobs, embedding cache entries, and message retrieval provenance. The local FAISS-style vector store persists a JSON index. Qdrant is available through the adapter when configured.

## Security

Documents, chunks, retrieval results, and citations are data, not instructions. The backend does not execute document content. Cloud embeddings are disabled by policy unless explicitly configured later.
