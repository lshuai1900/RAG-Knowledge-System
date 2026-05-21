import re
import hashlib
import logging
from datetime import datetime

from langchain_core.documents import Document

from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

# ── Chinese header detection patterns ──────────────────────────────────

# "一、项目背景" / "二、系统设计"
_CHINESE_NUMBER_HEADER = re.compile(
    r"^\s*[一二三四五六七八九十]+[、，]\s*\S"
)

# "（一）总体要求" / "（二）实施细则"
_CHINESE_PAREN_HEADER = re.compile(
    r"^\s*（[一二三四五六七八九十]+）\s*\S"
)

# "1. 概述" / "1.1 系统" / "1.1.1 细节" / "1）概述"
_DIGIT_DOT_HEADER = re.compile(
    r"^\s*\d+(?:\.\d+)*[.)、．\s]\s*\S"
)

# "第1章" / "第二章" / "第三节"
_CHAPTER_HEADER = re.compile(
    r"^\s*第[一二三四五六七八九十\d]+[章节条款]\s*\S"
)

# Markdown headers: # / ## / ### / etc.
_MARKDOWN_HEADER = re.compile(r"^(#{1,6})\s+\S")

# Short uppercase line: "INTRODUCTION" or "SYSTEM DESIGN"
_ENGLISH_SHORT_HEADER = re.compile(r"^[A-Z][A-Z\s\-]{3,50}$")

# Lines that are likely "section separators" (decorative lines)
_DECORATIVE_LINE = re.compile(r"^[=*\-_#]{5,}$")

# Lines that are page numbers / headers/footers
_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")

# ── List / table / formula patterns ────────────────────────────────────

_LIST_ITEM = re.compile(
    r"^\s*(?:[-•·●◆▪▸]|\d+[.)]|[a-zA-Z][.)]|（\d+）)\s+\S"
)

_TABLE_START = re.compile(
    r"^\s*(?:表|Table|表格)\s*\d*[:：].*|^\s*[|┃].*[|┃]\s*$"
)

# ── Header level mapping ───────────────────────────────────────────────

def _infer_level(line: str, match_type: str) -> int:
    """Infer header level (1=highest, 5=lowest) from match type and content."""
    if match_type == "chapter":
        # 第X章=1, 第X节=2, 第X条=3, 第X款=4
        suffix_map = {"章": 1, "节": 2, "条": 3, "款": 4}
        for suffix, lv in suffix_map.items():
            if suffix in line:
                return lv
        return 2
    if match_type == "chinese_number":
        return 2
    if match_type == "chinese_paren":
        return 3
    if match_type == "digit_dot":
        dots = line.strip().split()[0].count(".")
        if dots == 0:
            return 3  # "1. " → level 3
        return min(dots + 2, 5)  # "1.1" → 4, "1.1.1" → 5
    if match_type == "markdown_h1":
        return 1
    if match_type == "markdown_h2":
        return 2
    if match_type == "markdown_h3":
        return 3
    if match_type.startswith("markdown_h"):
        return min(int(match_type[-1]), 5)
    if match_type == "english_short":
        return 2
    return 3

# Max header level to consider (ignore too-deep nesting)
_MAX_LEVEL = 5


def _classify_header(line: str) -> tuple[str, int] | None:
    """If `line` looks like a section header, return (match_type, level)."""
    if _DECORATIVE_LINE.match(line):
        return None
    if _PAGE_NUMBER.match(line):
        return None

    # Chapter headers are strongest signal
    if _CHAPTER_HEADER.match(line):
        return ("chapter", _infer_level(line, "chapter"))
    # Chinese numbered sections
    if _CHINESE_NUMBER_HEADER.match(line):
        return ("chinese_number", _infer_level(line, "chinese_number"))
    # Parenthesized Chinese numbers like （一）
    if _CHINESE_PAREN_HEADER.match(line):
        return ("chinese_paren", _infer_level(line, "chinese_paren"))
    # Digit-dot patterns
    if _DIGIT_DOT_HEADER.match(line):
        return ("digit_dot", _infer_level(line, "digit_dot"))
    # Markdown headers
    m = _MARKDOWN_HEADER.match(line)
    if m:
        hashes = len(m.group(1))
        return (f"markdown_h{hashes}", _infer_level(line, f"markdown_h{hashes}"))
    # English short header
    if _ENGLISH_SHORT_HEADER.match(line):
        return ("english_short", _infer_level(line, "english_short"))
    return None


class SemanticChunker:
    """
    Splits documents into semantic chunks by detecting document structure
    (headers, sections, paragraphs) rather than using fixed-length splits.

    Designed for Chinese enterprise documents with mixed content types.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1500,
        doc_id: str = "",
        document_name: str = "",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.doc_id = doc_id
        self.document_name = document_name
        self._short_before = 0
        self._merged_short = 0

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """
        Main entry point. Takes raw Documents from a loader, returns
        semantically-split Documents with enriched metadata.
        """
        if not documents:
            return []

        # Merge all pages into a single text with page-offset tracking.
        # PyPDFLoader returns one Document per page; TextLoader returns one.
        text_parts = []
        page_map = []  # char_offset -> page_number

        for doc in documents:
            page_num = doc.metadata.get("page", None)
            start_offset = sum(len(t) for t in text_parts) + len(text_parts)  # + newlines
            text_parts.append(doc.page_content)
            if page_num is not None:
                page_map.append((start_offset, page_num))

        raw_text = "\n".join(text_parts)

        # Clean
        cleaned = clean_text(raw_text)
        raw_len = len(cleaned)

        # Detect structure
        headers = self._detect_structure(cleaned)

        # Split into semantic blocks
        blocks = self._split_by_structure(cleaned, headers)

        # Apply length control
        chunks_text = self._control_length(blocks)

        # Build Document objects with metadata
        result = self._build_documents(chunks_text, raw_len, headers, page_map)

        self._log_stats(raw_len, result)

        return result

    # ── Structure Detection ──────────────────────────────────────────

    def _detect_structure(self, text: str) -> list[dict]:
        """
        Scan text line-by-line. Return list of detected headers with
        positions and levels.

        Returns:
            [{char_start: int, char_end: int, title: str, level: int, match_type: str}]
        """
        headers = []
        lines = text.split("\n")
        pos = 0

        for line in lines:
            stripped = line.strip()

            if stripped:
                result = _classify_header(stripped)
                if result:
                    match_type, level = result
                    # Filter: headers should be reasonably short
                    if len(stripped) <= 60 or re.match(
                        r"^[一二三四五六七八九十\d]+[、.]", stripped
                    ):
                        headers.append({
                            "char_start": pos,
                            "char_end": pos + len(stripped),
                            "title": stripped,
                            "level": level,
                            "match_type": match_type,
                        })

            pos += len(line) + 1  # +1 for \n

        return self._dedupe_headers(headers)

    def _dedupe_headers(self, headers: list[dict]) -> list[dict]:
        """Remove duplicate header detections (same title in adjacent positions)."""
        if len(headers) <= 1:
            return headers
        result = [headers[0]]
        for h in headers[1:]:
            prev = result[-1]
            # Only dedup if same title detected very close (likely a false positive)
            if (h["title"] == prev["title"] and
                    h["char_start"] - prev["char_end"] < 50):
                continue
            result.append(h)
        return result

    # ── Semantic Splitting ───────────────────────────────────────────

    def _split_by_structure(self, text: str, headers: list[dict]) -> list[dict]:
        """
        Split text into blocks delimited by headers.
        Each header produces a block covering from its start to the
        next header, with section_path tracking ancestor headers.
        """
        if not headers:
            return self._split_by_paragraphs(text)

        # Prepend a virtual preamble header for text before the first detected header
        if headers[0]["char_start"] > 0:
            preamble = text[:headers[0]["char_start"]].strip()
            if preamble:
                headers.insert(0, {
                    "char_start": 0,
                    "char_end": 0,
                    "title": "",
                    "level": 0,
                    "match_type": "preamble",
                })

        blocks = []
        section_stack: list[tuple[str, int]] = []  # [(title, level), ...]

        for i, h in enumerate(headers):
            # Update section stack: pop headers of equal or higher level (larger level number)
            while section_stack and section_stack[-1][1] >= h["level"] and h["level"] > 0:
                section_stack.pop()
            if h["title"] and h["level"] > 0:
                section_stack.append((h["title"], h["level"]))

            # Content span: from after this header line to the next header.
            # Header text itself is metadata, not chunk content.
            content_start = h["char_end"] + 1  # +1 for the newline after header
            if i + 1 < len(headers):
                content_end = headers[i + 1]["char_start"]
            else:
                content_end = len(text)

            content = text[content_start:content_end].strip()

            if not content:
                continue

            section_path = " > ".join(t for t, _ in section_stack) if section_stack else ""

            blocks.append({
                "content": content,
                "section_title": h["title"],
                "section_path": section_path,
                "level": h["level"],
                "page": None,
            })

        return blocks

    def _split_by_paragraphs(self, text: str) -> list[dict]:
        """Fallback: split text by paragraph boundaries."""
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        return [{
            "content": p,
            "section_title": "",
            "section_path": "",
            "level": 0,
            "page": None,
        } for p in paragraphs]

    def _split_block_by_paragraphs(self, block: dict) -> list[dict]:
        """Split a single large block by paragraph boundaries."""
        paras = [p.strip() for p in re.split(r"\n\n+", block["content"]) if p.strip()]
        result = []
        for p in paras:
            result.append({
                "content": p,
                "section_title": block["section_title"],
                "section_path": block["section_path"],
                "level": block["level"],
                "page": block.get("page"),
            })
        return result

    # ── Length Control ────────────────────────────────────────────────

    def _control_length(self, blocks: list[dict]) -> list[dict]:
        """
        Merge short blocks and re-split long ones.
        Two-phase: forward merge, then backward merge for remaining orphans.
        """
        short_before = sum(1 for b in blocks if len(b["content"]) < self.min_chunk_size)

        # ── Phase A: forward merge (existing logic) ──
        result = []
        i = 0
        while i < len(blocks):
            block = blocks[i]
            content_len = len(block["content"])

            if content_len < self.min_chunk_size and result:
                prev = result[-1]
                merged_content = prev["content"] + "\n\n" + block["content"]
                if prev["level"] <= block["level"]:
                    merged_title = prev["section_title"]
                    merged_path = prev["section_path"]
                    merged_level = prev["level"]
                else:
                    merged_title = block["section_title"]
                    merged_path = block["section_path"]
                    merged_level = block["level"]
                result[-1] = {
                    "content": merged_content,
                    "section_title": merged_title,
                    "section_path": merged_path,
                    "level": merged_level,
                    "page": prev.get("page"),
                }
            elif content_len > self.max_chunk_size:
                sub_parts = self._split_by_sentences(block["content"], block)
                result.extend(sub_parts)
            else:
                result.append(block)
            i += 1

        # ── Phase B: backward merge — if the first block is still too short,
        # merge it forward into the next block (or later blocks if needed) ──
        if result and len(result[0]["content"]) < self.min_chunk_size and len(result) > 1:
            # Merge result[0] → result[1]; prefer result[1]'s metadata
            target = result[1]
            orphan = result[0]
            merged_content = orphan["content"] + "\n\n" + target["content"]
            result[1] = {
                "content": merged_content,
                "section_title": target["section_title"] or orphan["section_title"],
                "section_path": target["section_path"] or orphan["section_path"],
                "level": target["level"],
                "page": target.get("page"),
            }
            result.pop(0)

        # ── Phase C: trailing orphan — if the last block is still too short,
        # merge it backward into the second-to-last block ──
        if len(result) > 1 and len(result[-1]["content"]) < self.min_chunk_size:
            orphan = result.pop()
            prev = result[-1]
            merged_content = prev["content"] + "\n\n" + orphan["content"]
            result[-1] = {
                "content": merged_content,
                "section_title": prev["section_title"] or orphan["section_title"],
                "section_path": prev["section_path"] or orphan["section_path"],
                "level": prev["level"],
                "page": prev.get("page"),
            }

        self._short_before = short_before
        self._merged_short = short_before - sum(
            1 for b in result if len(b["content"]) < self.min_chunk_size
        )

        return result

    def _split_by_sentences(self, text: str, parent: dict) -> list[dict]:
        """Split a too-long block by sentence boundaries with overlap."""
        sentences = re.split(r"(?<=[。！？!?])\s*", text)
        chunks = []
        current = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if (len(current) + len(sent) > self.max_chunk_size and
                    len(current) >= self.min_chunk_size):
                chunks.append(current.strip())
                # Carry overlap from the end of the previous chunk
                if self.chunk_overlap > 0 and len(current) > self.chunk_overlap:
                    overlap_text = current[-self.chunk_overlap:]
                    # Start at the last sentence boundary within the overlap
                    boundary = max(
                        overlap_text.rfind("。"), overlap_text.rfind("！"),
                        overlap_text.rfind("？"), overlap_text.rfind("."),
                        overlap_text.rfind("!"), overlap_text.rfind("?"),
                    )
                    if boundary > 0:
                        current = overlap_text[boundary + 1:].strip() + " " + sent
                    else:
                        current = sent
                else:
                    current = sent
            else:
                if current:
                    current += " " + sent
                else:
                    current = sent
        if current.strip():
            chunks.append(current.strip())

        if not chunks:
            return [parent]

        return [{
            "content": c,
            "section_title": parent["section_title"],
            "section_path": parent["section_path"],
            "level": parent["level"],
            "page": parent.get("page"),
        } for c in chunks]

    # ── Metadata & Document Building ────────────────────────────────

    def _build_documents(
        self,
        chunks_text: list[dict],
        raw_len: int,
        headers: list[dict],
        page_map: list[tuple[int, int]],
    ) -> list[Document]:
        """Convert chunk dicts to LangChain Documents with metadata."""

        # Build a sorted list of header positions for page mapping
        # page_map: [(char_offset, page_num), ...]
        # We'll estimate page for each chunk based on its approximate position

        documents = []
        for idx, chunk in enumerate(chunks_text):
            content = chunk["content"]
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:8]

            chunk_id = f"{self.doc_id}_{idx}_{content_hash}" if self.doc_id else f"{idx}_{content_hash}"

            # Estimate page from content position (rough heuristic)
            # Match the chunk start with the original text
            # We don't have exact char position here since we're working with
            # processed blocks, but we can estimate.
            page = self._estimate_page(chunk, page_map)

            metadata = {
                "chunk_id": chunk_id,
                "doc_id": self.doc_id,
                "document_name": self.document_name,
                "chunk_index": idx,
                "section_title": chunk.get("section_title", ""),
                "section_path": chunk.get("section_path", ""),
                "page": page,
                "content_length": len(content),
                "created_at": datetime.utcnow().isoformat(),
            }

            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)

        return documents

    def _estimate_page(
        self, chunk: dict, page_map: list[tuple[int, int]]
    ) -> int | None:
        """Estimate page number for a chunk based on page_map heuristics."""
        if not page_map:
            return None
        # For now, return the most likely page based on section number
        # This is a heuristic — exact page matching requires tracking
        # offsets through the full pipeline.
        # PyPDFLoader's page numbers are 0-indexed, we store as-is.
        return None  # We'll set this from the loader metadata in document_service

    # ── Logging ──────────────────────────────────────────────────────

    def _log_stats(self, raw_len: int, chunks: list[Document]) -> None:
        if not chunks:
            logger.warning(
                "[SemanticChunker] document=%s raw_len=%d chunks=0",
                self.document_name, raw_len,
            )
            return

        lengths = [len(doc.page_content) for doc in chunks]
        short_after = sum(1 for l in lengths if l < self.min_chunk_size)
        long_count = sum(1 for l in lengths if l > self.max_chunk_size)
        structure_count = sum(
            1 for doc in chunks if doc.metadata.get("section_title")
        )

        logger.info(
            "[SemanticChunker] document=%s raw_len=%d chunks=%d avg_len=%d "
            "min_len=%d max_len=%d short_before=%d short_after=%d merged=%d "
            "long_chunks=%d with_sections=%d",
            self.document_name, raw_len, len(chunks),
            sum(lengths) // len(chunks) if chunks else 0,
            min(lengths) if chunks else 0,
            max(lengths) if chunks else 0,
            getattr(self, "_short_before", 0),
            short_after,
            getattr(self, "_merged_short", 0),
            long_count, structure_count,
        )
