"""Recursive text chunker — default strategy for unstructured documents."""

from __future__ import annotations

import os
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.core.base import BaseChunker
from rag.core.schemas import ChunkRecord


class RecursiveChunker(BaseChunker):
    name = "recursive"

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "800"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "120"))
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
        )

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        meta = metadata or {}
        docs = self._splitter.create_documents([text])
        chunks = []
        for i, doc in enumerate(docs):
            content = doc.page_content
            chunks.append(ChunkRecord(
                chunk_id=f"{meta.get('doc_id', 'doc')}_{i}",
                doc_id=meta.get("doc_id", ""),
                kb_id=meta.get("kb_id", ""),
                text=content,
                chunk_index=i,
                char_count=len(content),
                token_estimate=len(content) // 2,
                chunk_strategy=self.name,
                parser_name=meta.get("parser_name", ""),
                file_type=meta.get("file_type", ""),
                filename=meta.get("filename", ""),
            ))
        return chunks
