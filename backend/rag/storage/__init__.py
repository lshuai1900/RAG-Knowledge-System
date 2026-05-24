"""Storage abstraction — Document / Chunk / Vector / Metadata stores.

All file I/O for RAG data goes through these classes.
Business logic should NOT open JSON / numpy files directly.
"""

from .document_store import DocumentStore, ChunkStore, VectorStore
