"""Unified Parser abstraction for document-to-text conversion.

Each parser takes a file path and returns a standardised dict with
``text`` and ``metadata``.  This module does NOT replace
``yuxi_rag/parser.py`` — it lives alongside as a structured API for
future ingestion flows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ParseResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "metadata": dict(self.metadata)}


@dataclass(slots=True)
class ParseError:
    path: Path
    error: str
    parser: str = "unknown"


class BaseParser(ABC):
    """Abstract parser — implement for each supported file type."""

    name: str = "base"

    @abstractmethod
    def parse(self, path: Path) -> ParseResult:
        ...

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.accepts()

    @classmethod
    @abstractmethod
    def accepts(cls) -> set[str]:
        """Return the set of lower-case extensions this parser handles."""
        ...


def format_parse_result(parser_name: str, text: str, *, filename: str, file_type: str, **extra: Any) -> ParseResult:
    return ParseResult(
        text=text,
        metadata={
            "filename": filename,
            "file_type": file_type,
            "parser": parser_name,
            **extra,
        },
    )
