from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .parser import ParsedParagraph
except ImportError:  # pragma: no cover - direct script fallback
    from parser import ParsedParagraph

RAG_LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS_PATH = RAG_LAB_DIR / "data" / "chunks" / "chunks.json"
_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\.])\s*")


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    chunk_text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "chunk_text": self.chunk_text,
            "metadata": self.metadata,
        }


def _overlap_text(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return ""
    return text[-overlap:].strip()


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        sentences = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            step = max(1, chunk_size - chunk_overlap)
            while start < len(sentence):
                chunks.append(sentence[start:start + chunk_size].strip())
                start += step
            continue

        candidate = f"{current}\n{sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size or not current:
            current = candidate
            continue
        chunks.append(current.strip())
        overlap = _overlap_text(current, chunk_overlap)
        current = f"{overlap}\n{sentence}".strip() if overlap else sentence

    if current.strip():
        chunks.append(current.strip())
    return chunks


def _metadata_for_group(group: list[ParsedParagraph], source_index: int, chunk_index: int) -> dict[str, Any]:
    first = group[0].metadata
    last = group[-1].metadata
    pages = [item.metadata.get("page") for item in group if item.metadata.get("page") is not None]
    metadata = {
        "source": first.get("source", ""),
        "file_id": first.get("file_id", ""),
        "extension": first.get("extension", ""),
        "chunk_index": chunk_index,
        "paragraph_start": first.get("paragraph"),
        "paragraph_end": last.get("paragraph"),
        "source_index": source_index,
    }
    if pages:
        metadata["page"] = pages[0]
        metadata["page_start"] = min(pages)
        metadata["page_end"] = max(pages)
    return metadata


def chunk_paragraphs(
    paragraphs: list[ParsedParagraph],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[ParsedParagraph] = []
    current_text = ""
    source_index: dict[str, int] = {}
    chunk_counts: dict[str, int] = {}

    def flush() -> None:
        nonlocal current, current_text
        if not current or not current_text.strip():
            current = []
            current_text = ""
            return
        source = str(current[0].metadata.get("source", ""))
        idx = chunk_counts.get(source, 0)
        chunk_counts[source] = idx + 1
        source_idx = source_index.setdefault(source, len(source_index))
        metadata = _metadata_for_group(current, source_idx, idx)
        chunk_id = f"{metadata.get('file_id') or source_idx}_chunk_{idx}"
        chunks.append(Chunk(chunk_id=chunk_id, chunk_text=current_text.strip(), metadata=metadata))
        current = []
        current_text = ""

    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        source = paragraph.metadata.get("source")
        if current and current[0].metadata.get("source") != source:
            flush()

        if len(text) > chunk_size:
            flush()
            source_key = str(source or "")
            source_idx = source_index.setdefault(source_key, len(source_index))
            base_idx = chunk_counts.get(source_key, 0)
            parts = _split_long_text(text, chunk_size, chunk_overlap)
            for offset, part in enumerate(parts):
                idx = base_idx + offset
                metadata = dict(paragraph.metadata)
                metadata.update({
                    "chunk_index": idx,
                    "paragraph_start": paragraph.metadata.get("paragraph"),
                    "paragraph_end": paragraph.metadata.get("paragraph"),
                    "source_index": source_idx,
                })
                chunk_id = f"{metadata.get('file_id') or source_idx}_chunk_{idx}"
                chunks.append(Chunk(chunk_id=chunk_id, chunk_text=part, metadata=metadata))
            chunk_counts[source_key] = base_idx + len(parts)
            continue

        candidate = f"{current_text}\n\n{text}".strip() if current_text else text
        if current and len(candidate) > chunk_size:
            previous_text = current_text
            flush()
            overlap = _overlap_text(previous_text, chunk_overlap)
            if overlap:
                overlap_para = ParsedParagraph(
                    text=overlap,
                    metadata={**paragraph.metadata, "paragraph": paragraph.metadata.get("paragraph")},
                )
                current = [overlap_para, paragraph]
                current_text = f"{overlap}\n\n{text}".strip()
            else:
                current = [paragraph]
                current_text = text
        else:
            current.append(paragraph)
            current_text = candidate

    flush()
    return chunks


def save_chunks(chunks: list[Chunk], output_path: str | Path = DEFAULT_CHUNKS_PATH) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([chunk.to_dict() for chunk in chunks], f, ensure_ascii=False, indent=2)


def load_chunks(path: str | Path = DEFAULT_CHUNKS_PATH) -> list[Chunk]:
    with Path(path).open("r", encoding="utf-8") as f:
        rows = json.load(f)
    return [Chunk(chunk_id=row["chunk_id"], chunk_text=row["chunk_text"], metadata=row.get("metadata", {})) for row in rows]
