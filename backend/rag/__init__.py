"""RAG Knowledge System — Yuxi-style modular architecture.

Reference: https://github.com/xerrors/Yuxi

Package layout::

    rag/
        core/        Manager, Factory, Schemas, Exceptions
        parsers/     Document parsers (txt, md, pdf, docx)
        chunking/    Chunk strategies + dispatcher
        embeddings/  Embedding providers (openai, dashscope, hash)
        retrieval/   Dense, sparse, hybrid, fusion, rerank
        storage/     Document, chunk, vector, metadata stores
        status/      Runtime state + health
        evaluation/  Dataset, runner, metrics, report
"""

__version__ = "0.2.0"
