"""Sentence-window chunker — Chinese punctuation-aware sliding window."""

from __future__ import annotations

import re
from typing import Any

from rag.core.base import BaseChunker
from rag.core.schemas import ChunkRecord

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\.])\s*")


class SentenceWindowChunker(BaseChunker):
    name = "sentence_window"

    def __init__(self, window_size: int = 600, overlap_sentences: int = 2):
        self.window_size = window_size
        self.overlap_sentences = overlap_sentences

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        meta = metadata or {}
        doc_id = meta.get("doc_id", "")
        kb_id = meta.get("kb_id", "")
        fname = meta.get("filename", "")
        parser_name = meta.get("parser_name", "")
        file_type = meta.get("file_type", "")

        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        if not sentences:
            sentences = [text]

        chunks = []
        idx = 0
        i = 0
        while i < len(sentences):
            window = sentences[i]
            j = i + 1
            while j < len(sentences) and len(window) + len(sentences[j]) + 1 <= self.window_size:
                window += " " + sentences[j]
                j += 1

            chunks.append(ChunkRecord(
                chunk_id=f"{doc_id}_{idx}", doc_id=doc_id, kb_id=kb_id,
                text=window, chunk_index=idx,
                char_count=len(window), token_estimate=len(window) // 2,
                chunk_strategy=self.name,
                parser_name=parser_name, file_type=file_type, filename=fname,
                metadata={"sentence_start": i, "sentence_end": j - 1},
            ))
            idx += 1

            if j == i:
                i += 1
            else:
                i = max(i + 1, j - self.overlap_sentences)

        return chunks
