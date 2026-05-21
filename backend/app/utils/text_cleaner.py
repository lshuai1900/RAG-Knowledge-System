import re

# Characters to strip from start/end of lines
_STRIP_CHARS = " \t\r\n﻿　"

# Patterns to detect lines that are likely section headers (should not be merged)
_HEADER_PATTERNS = [
    re.compile(r"^\s*[一二三四五六七八九十]+[、，]\s*\S"),    # 一、 / 二、
    re.compile(r"^\s*（[一二三四五六七八九十]+）\s*\S"),       # （一） / （二）
    re.compile(r"^\s*\d+(?:\.\d+)*[.)、．\s]\s*\S"),           # 1. / 1.1 / 1）
    re.compile(r"^\s*第[一二三四五六七八九十\d]+[章节条款]\s*\S"),   # 第X章
    re.compile(r"^(#{1,6})\s+\S"),                            # Markdown headers
    re.compile(r"^[A-Z][A-Z\s\-]{3,50}$"),                   # Short English headers
]


def clean_text(text: str) -> str:
    """
    Clean raw document text for better chunking quality.
    Applies a sequence of normalization steps suitable for Chinese documents.
    """
    if not text:
        return ""

    # 1. Remove BOM / zero-width characters
    text = text.replace("﻿", "").replace("​", "")

    # 2. Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Normalize Chinese full-width spaces to half-width
    text = text.replace("　", " ")

    # 4. Merge single line breaks within paragraphs (PDF hard-break artifact)
    # A single \n between non-empty, non-header, non-punctuation-ending lines
    # is likely a PDF formatting artifact, not a real paragraph break.
    lines = text.split("\n")
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

        if (i + 1 < len(lines) and
                stripped and next_line and
                not _looks_like_header(stripped) and
                not _line_looks_complete(line) and
                not _looks_like_header(next_line)):
            merged.append(stripped + " " + next_line)
            i += 2
        else:
            merged.append(line)
            i += 1
    text = "\n".join(merged)

    # 5. Collapse 3+ consecutive newlines to exactly 2 (paragraph boundary)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 6. Collapse multiple spaces (but not newlines)
    text = re.sub(r"[ ]{2,}", " ", text)

    # 7. Strip each line but preserve leading whitespace for structure detection
    text = "\n".join(
        line.strip(_STRIP_CHARS) if line.strip(_STRIP_CHARS) else ""
        for line in text.split("\n")
    )

    # 8. Normalize common Chinese punctuation variants
    text = text.replace("︰", "：")   # presentation form colon
    text = text.replace("﹔", "；")   # small semicolon
    text = text.replace("﹖", "？")   # small question mark

    return text.strip()


def _looks_like_header(line: str) -> bool:
    """Check if a line looks like a section header that should not be merged."""
    return any(pat.match(line) for pat in _HEADER_PATTERNS)


def _line_looks_complete(line: str) -> bool:
    """
    Check if a line ends with sentence/clause-ending punctuation.
    If not, it's likely broken mid-sentence (PDF artifact).
    """
    line = line.strip()
    if not line:
        return True
    endings = frozenset("。！？；：）》\"!?;:.")
    return any(line.endswith(c) for c in endings)


