"""Paragraph chunker — split by double newline, sub-split long paragraphs."""

from __future__ import annotations

from typing import Any

from rag.core.base import BaseChunker
from rag.core.schemas import ChunkRecord


class ParagraphChunker(BaseChunker):
    name = "paragraph"

    def __init__(self, max_chunk_size: int = 1500):
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        meta = metadata or {}
        doc_id = meta.get("doc_id", "")
        kb_id = meta.get("kb_id", "")
        fname = meta.get("filename", "")
        parser_name = meta.get("parser_name", "")
        file_type = meta.get("file_type", "")

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        chunks = []
        idx = 0
        for para in paragraphs:
            if len(para) <= self.max_chunk_size:
                chunks.append(ChunkRecord(
                    chunk_id=f"{doc_id}_{idx}", doc_id=doc_id, kb_id=kb_id,
                    text=para, chunk_index=idx,
                    char_count=len(para), token_estimate=len(para) // 2,
                    chunk_strategy=self.name,
                    parser_name=parser_name, file_type=file_type, filename=fname,
                ))
                idx += 1
            else:
                for offset in range(0, len(para), self.max_chunk_size):
                    sub = para[offset:offset + self.max_chunk_size]
                    chunks.append(ChunkRecord(
                        chunk_id=f"{doc_id}_{idx}", doc_id=doc_id, kb_id=kb_id,
                        text=sub, chunk_index=idx,
                        char_count=len(sub), token_estimate=len(sub) // 2,
                        chunk_strategy=self.name,
                        parser_name=parser_name, file_type=file_type, filename=fname,
                        start_char=offset,
                        end_char=min(offset + self.max_chunk_size, len(para)),
                    ))
                    idx += 1
        return chunks
