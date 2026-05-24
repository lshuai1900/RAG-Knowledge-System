"""Markdown header-aware chunker — respects # heading hierarchy."""

from __future__ import annotations

import re
from typing import Any

from rag.core.base import BaseChunker
from rag.core.schemas import ChunkRecord

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownHeaderChunker(BaseChunker):
    name = "markdown_header"

    def __init__(self, max_chunk_size: int = 2000):
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[ChunkRecord]:
        meta = metadata or {}
        doc_id = meta.get("doc_id", "")
        kb_id = meta.get("kb_id", "")
        fname = meta.get("filename", "")
        parser_name = meta.get("parser_name", "")
        file_type = meta.get("file_type", "")

        headings = list(_HEADING_RE.finditer(text))
        if not headings:
            # Fall back to single chunk
            return [ChunkRecord(
                chunk_id=f"{doc_id}_0", doc_id=doc_id, kb_id=kb_id,
                text=text[:self.max_chunk_size],
                chunk_index=0, char_count=min(len(text), self.max_chunk_size),
                token_estimate=min(len(text), self.max_chunk_size) // 2,
                chunk_strategy=self.name,
                parser_name=parser_name, file_type=file_type, filename=fname,
            )]

        sections: list[tuple[str, str | None, str]] = []
        for i, match in enumerate(headings):
            title = match.group(2).strip()
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            sections.append((body, title, title))

        if headings and headings[0].start() > 0:
            preamble = text[:headings[0].start()].strip()
            if preamble:
                sections.insert(0, (preamble, None, ""))

        chunks = []
        idx = 0
        for body, section_path, section_title in sections:
            if not body:
                continue
            if len(body) <= self.max_chunk_size:
                chunks.append(ChunkRecord(
                    chunk_id=f"{doc_id}_{idx}", doc_id=doc_id, kb_id=kb_id,
                    text=body, chunk_index=idx,
                    char_count=len(body), token_estimate=len(body) // 2,
                    chunk_strategy=self.name,
                    parser_name=parser_name, file_type=file_type, filename=fname,
                    section_title=section_title or "",
                    section_path=section_path or "",
                ))
                idx += 1
            else:
                # Split long sections
                for offset in range(0, len(body), self.max_chunk_size):
                    sub = body[offset:offset + self.max_chunk_size]
                    chunks.append(ChunkRecord(
                        chunk_id=f"{doc_id}_{idx}", doc_id=doc_id, kb_id=kb_id,
                        text=sub, chunk_index=idx,
                        char_count=len(sub), token_estimate=len(sub) // 2,
                        chunk_strategy=self.name,
                        parser_name=parser_name, file_type=file_type, filename=fname,
                        section_title=section_title or "",
                        section_path=section_path or "",
                        start_char=offset, end_char=min(offset + self.max_chunk_size, len(body)),
                    ))
                    idx += 1
        return chunks
