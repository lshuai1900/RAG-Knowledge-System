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
SUPPORTED_CHUNK_STRATEGIES = {"paragraph", "recursive", "sentence_window", "markdown_header"}


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


@dataclass(slots=True)
class _ChunkUnit:
    text: str
    metadata: dict[str, Any]
    start_char: int
    end_char: int


def _normalize_strategy(strategy: str | None) -> str:
    if not strategy:
        return "paragraph"
    normalized = strategy.strip().lower()
    if normalized == "semantic":
        return "paragraph"
    return normalized


def normalize_chunk_strategy(strategy: str | None) -> str:
    return _normalize_strategy(strategy)


def _build_paragraph_offsets(paragraphs: list[ParsedParagraph]) -> dict[tuple[str, int], int]:
    offsets: dict[tuple[str, int], int] = {}
    current_offsets: dict[str, int] = {}
    for paragraph in paragraphs:
        source = str(paragraph.metadata.get("source", ""))
        idx = int(paragraph.metadata.get("paragraph", 0))
        offset = current_offsets.get(source, 0)
        offsets[(source, idx)] = offset
        current_offsets[source] = offset + len(paragraph.text) + 2
    return offsets


def _slice_text(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[str, int, int]]:
    if not text:
        return []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    chunks: list[tuple[str, int, int]] = []
    while start < len(text):
        end = min(len(text), start + chunk_size)
        window = text[start:end]
        leading = len(window) - len(window.lstrip())
        trailing = len(window) - len(window.rstrip())
        trimmed = window.strip()
        if trimmed:
            chunk_start = start + leading
            chunk_end = end - trailing
            chunks.append((trimmed, chunk_start, chunk_end))
        if end == len(text):
            break
        start += step
    return chunks


def _metadata_for_group(
    group: list[ParsedParagraph],
    source_index: int,
    chunk_index: int,
    start_char: int,
    end_char: int,
    chunk_strategy: str,
) -> dict[str, Any]:
    first = group[0].metadata
    last = group[-1].metadata
    pages = [item.metadata.get("page") for item in group if item.metadata.get("page") is not None]
    paragraph_start = first.get("paragraph")
    paragraph_end = last.get("paragraph")
    metadata = {
        "source": first.get("source", ""),
        "file_id": first.get("file_id", ""),
        "extension": first.get("extension", ""),
        "chunk_index": chunk_index,
        "paragraph": paragraph_start,
        "paragraph_start": paragraph_start,
        "paragraph_end": paragraph_end,
        "source_index": source_index,
        "chunk_strategy": chunk_strategy,
        "start_char": int(start_char),
        "end_char": int(end_char),
    }
    if pages:
        metadata["page"] = pages[0]
        metadata["page_start"] = min(pages)
        metadata["page_end"] = max(pages)
    else:
        metadata["page"] = None
    return metadata


def _chunk_units(
    units: list[_ChunkUnit],
    chunk_size: int,
    chunk_overlap: int,
    chunk_strategy: str,
    source_index: dict[str, int],
    chunk_counts: dict[str, int],
    joiner: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[_ChunkUnit] = []
    current_len = 0
    current_source: str | None = None

    def _flush() -> list[_ChunkUnit]:
        nonlocal current, current_len, current_source
        if not current:
            current_len = 0
            current_source = None
            return []
        source = current_source or str(current[0].metadata.get("source", ""))
        idx = chunk_counts.get(source, 0)
        chunk_counts[source] = idx + 1
        source_idx = source_index.setdefault(source, len(source_index))
        start_char = current[0].start_char
        end_char = current[-1].end_char
        metadata = _metadata_for_group(
            [ParsedParagraph(text=u.text, metadata=u.metadata) for u in current],
            source_idx,
            idx,
            start_char,
            end_char,
            chunk_strategy,
        )
        chunk_id = f"{metadata.get('file_id') or source_idx}_chunk_{idx}"
        chunk_text = joiner.join(u.text for u in current).strip()
        chunks.append(Chunk(chunk_id=chunk_id, chunk_text=chunk_text, metadata=metadata))
        flushed = current
        current = []
        current_len = 0
        current_source = None
        return flushed

    def _carry_overlap(flushed_units: list[_ChunkUnit]) -> list[_ChunkUnit]:
        if chunk_overlap <= 0:
            return []
        overlap_units: list[_ChunkUnit] = []
        total = 0
        for unit in reversed(flushed_units):
            overlap_units.insert(0, unit)
            total += len(unit.text)
            if total >= chunk_overlap:
                break
        return overlap_units

    for unit in units:
        source = str(unit.metadata.get("source", ""))
        if current and current_source != source:
            _flush()

        unit_len = len(unit.text)
        if current and current_len + unit_len + len(joiner) > chunk_size:
            flushed = _flush()
            overlap_units = _carry_overlap(flushed)
            if overlap_units:
                current = overlap_units
                current_len = sum(len(u.text) for u in current)
                current_source = str(current[0].metadata.get("source", ""))
        if not current:
            current_source = source
        current.append(unit)
        current_len += unit_len

    _flush()
    return chunks


def _paragraph_units(
    paragraphs: list[ParsedParagraph],
    chunk_size: int,
    chunk_overlap: int,
) -> list[_ChunkUnit]:
    offsets = _build_paragraph_offsets(paragraphs)
    units: list[_ChunkUnit] = []
    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        source = str(paragraph.metadata.get("source", ""))
        para_idx = int(paragraph.metadata.get("paragraph", 0))
        base_offset = offsets.get((source, para_idx), 0)
        if len(text) > chunk_size:
            parts = _slice_text(text, chunk_size, chunk_overlap)
            for part_text, part_start, part_end in parts:
                units.append(_ChunkUnit(
                    text=part_text,
                    metadata=dict(paragraph.metadata),
                    start_char=base_offset + part_start,
                    end_char=base_offset + part_end,
                ))
        else:
            units.append(_ChunkUnit(
                text=text,
                metadata=dict(paragraph.metadata),
                start_char=base_offset,
                end_char=base_offset + len(text),
            ))
    return units


def _sentence_units(
    paragraphs: list[ParsedParagraph],
    chunk_size: int,
    chunk_overlap: int,
) -> list[_ChunkUnit]:
    offsets = _build_paragraph_offsets(paragraphs)
    units: list[_ChunkUnit] = []
    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        source = str(paragraph.metadata.get("source", ""))
        para_idx = int(paragraph.metadata.get("paragraph", 0))
        base_offset = offsets.get((source, para_idx), 0)
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        if not sentences:
            sentences = [text]
        cursor = 0
        for sentence in sentences:
            start = text.find(sentence, cursor)
            if start < 0:
                start = cursor
            end = start + len(sentence)
            cursor = end
            if len(sentence) > chunk_size:
                parts = _slice_text(sentence, chunk_size, chunk_overlap)
                for part_text, part_start, part_end in parts:
                    units.append(_ChunkUnit(
                        text=part_text,
                        metadata=dict(paragraph.metadata),
                        start_char=base_offset + start + part_start,
                        end_char=base_offset + start + part_end,
                    ))
            else:
                units.append(_ChunkUnit(
                    text=sentence,
                    metadata=dict(paragraph.metadata),
                    start_char=base_offset + start,
                    end_char=base_offset + end,
                ))
    return units


def _chunk_recursive(
    paragraphs: list[ParsedParagraph],
    chunk_size: int,
    chunk_overlap: int,
    chunk_strategy: str,
) -> list[Chunk]:
    offsets = _build_paragraph_offsets(paragraphs)
    source_texts: dict[str, str] = {}
    source_paragraphs: dict[str, list[ParsedParagraph]] = {}
    for paragraph in paragraphs:
        source = str(paragraph.metadata.get("source", ""))
        source_paragraphs.setdefault(source, []).append(paragraph)

    for source, paras in source_paragraphs.items():
        pieces = [p.text.strip() for p in paras if p.text.strip()]
        source_texts[source] = "\n\n".join(pieces)

    chunks: list[Chunk] = []
    source_index: dict[str, int] = {}
    chunk_counts: dict[str, int] = {}
    for source, text in source_texts.items():
        if not text:
            continue
        first_meta = source_paragraphs.get(source, [ParsedParagraph(text="", metadata={})])[0].metadata
        spans: list[tuple[int, int, int, int | None]] = []
        for paragraph in source_paragraphs.get(source, []):
            para_idx = int(paragraph.metadata.get("paragraph", 0))
            start = offsets.get((source, para_idx), 0)
            end = start + len(paragraph.text)
            spans.append((start, end, para_idx, paragraph.metadata.get("page")))

        parts = _slice_text(text, chunk_size, chunk_overlap)
        for part_text, start_char, end_char in parts:
            paragraph_idx = spans[0][2] if spans else 0
            page = spans[0][3] if spans else None
            for span_start, span_end, para_idx, para_page in spans:
                if span_start <= start_char < span_end:
                    paragraph_idx = para_idx
                    page = para_page
                    break
            idx = chunk_counts.get(source, 0)
            chunk_counts[source] = idx + 1
            source_idx = source_index.setdefault(source, len(source_index))
            metadata = {
                "source": source,
                "file_id": first_meta.get("file_id", ""),
                "extension": first_meta.get("extension", ""),
                "chunk_index": idx,
                "paragraph": paragraph_idx,
                "paragraph_start": paragraph_idx,
                "paragraph_end": paragraph_idx,
                "source_index": source_idx,
                "chunk_strategy": chunk_strategy,
                "start_char": int(start_char),
                "end_char": int(end_char),
                "page": page,
            }
            chunk_id = f"{source_idx}_chunk_{idx}"
            chunks.append(Chunk(chunk_id=chunk_id, chunk_text=part_text, metadata=metadata))
    return chunks


def _chunk_markdown_header(
    paragraphs: list[ParsedParagraph],
    chunk_size: int,
    chunk_overlap: int,
    chunk_strategy: str,
) -> list[Chunk]:
    sections: list[list[ParsedParagraph]] = []
    current: list[ParsedParagraph] = []
    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if text.startswith("#"):
            if current:
                sections.append(current)
            current = [paragraph]
        else:
            current.append(paragraph)
    if current:
        sections.append(current)

    source_index: dict[str, int] = {}
    chunk_counts: dict[str, int] = {}
    chunks: list[Chunk] = []
    for section in sections:
        units = _paragraph_units(section, chunk_size, chunk_overlap)
        chunks.extend(_chunk_units(
            units,
            chunk_size,
            chunk_overlap,
            chunk_strategy,
            source_index,
            chunk_counts,
            joiner="\n\n",
        ))
    return chunks


def chunk_documents(
    paragraphs: list[ParsedParagraph],
    chunk_strategy: str | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    strategy = _normalize_strategy(chunk_strategy)
    if strategy not in SUPPORTED_CHUNK_STRATEGIES:
        raise ValueError(f"Unsupported chunk strategy: {strategy}")

    if strategy == "recursive":
        return _chunk_recursive(paragraphs, chunk_size, chunk_overlap, strategy)

    source_index: dict[str, int] = {}
    chunk_counts: dict[str, int] = {}
    if strategy == "sentence_window":
        units = _sentence_units(paragraphs, chunk_size, chunk_overlap)
        return _chunk_units(
            units,
            chunk_size,
            chunk_overlap,
            strategy,
            source_index,
            chunk_counts,
            joiner=" ",
        )

    if strategy == "markdown_header":
        return _chunk_markdown_header(paragraphs, chunk_size, chunk_overlap, strategy)

    units = _paragraph_units(paragraphs, chunk_size, chunk_overlap)
    return _chunk_units(
        units,
        chunk_size,
        chunk_overlap,
        strategy,
        source_index,
        chunk_counts,
        joiner="\n\n",
    )


def chunk_paragraphs(
    paragraphs: list[ParsedParagraph],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    return chunk_documents(
        paragraphs,
        chunk_strategy="paragraph",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def save_chunks(chunks: list[Chunk], output_path: str | Path = DEFAULT_CHUNKS_PATH) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([chunk.to_dict() for chunk in chunks], f, ensure_ascii=False, indent=2)


def load_chunks(path: str | Path = DEFAULT_CHUNKS_PATH) -> list[Chunk]:
    with Path(path).open("r", encoding="utf-8") as f:
        rows = json.load(f)
    return [Chunk(chunk_id=row["chunk_id"], chunk_text=row["chunk_text"], metadata=row.get("metadata", {})) for row in rows]
