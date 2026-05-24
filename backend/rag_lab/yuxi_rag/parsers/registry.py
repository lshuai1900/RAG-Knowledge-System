from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParseResult, ParseError
from .txt_parser import TextParser
from .pdf_parser import PdfParser
from .docx_parser import DocxParser


_builtin: list[BaseParser] = [TextParser(), PdfParser(), DocxParser()]


def get_parser(extension: str) -> BaseParser | None:
    ext = extension.lower()
    for parser in _builtin:
        if parser.supports(ext):
            return parser
    return None


def parse_file(path: Path) -> ParseResult:
    ext = path.suffix.lower()
    parser = get_parser(ext)
    if parser is None:
        raise ValueError(f"Unsupported file type: {ext} (path={path})")
    return parser.parse(path)


def parse_files(paths: list[Path]) -> tuple[list[ParseResult], list[ParseError]]:
    results: list[ParseResult] = []
    errors: list[ParseError] = []
    for path in paths:
        try:
            results.append(parse_file(path))
        except Exception as exc:
            errors.append(ParseError(path=path, error=str(exc), parser="auto"))
    return results, errors


def supported_extensions() -> set[str]:
    exts: set[str] = set()
    for parser in _builtin:
        exts.update(parser.accepts())
    return exts
