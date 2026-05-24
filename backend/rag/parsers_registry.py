"""Built-in parser implementations — used when yuxi_rag.parsers is unavailable."""

from __future__ import annotations

from pathlib import Path
from rag.core.base import BaseParser
from rag.core.schemas import ParseResult


class TextParser(BaseParser):
    name = "text"

    @classmethod
    def accepts(cls) -> set[str]:
        return {".txt", ".md", ".markdown"}

    def parse(self, path: Path) -> ParseResult:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                text = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
        return ParseResult(
            text=text, filename=path.name,
            file_type=path.suffix.lower().lstrip("."),
            parser_name=self.name, char_count=len(text),
        )


class PdfParser(BaseParser):
    name = "pdf"

    @classmethod
    def accepts(cls) -> set[str]:
        return {".pdf"}

    def parse(self, path: Path) -> ParseResult:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("pypdf is required to parse PDF files") from exc
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
        return ParseResult(
            text=text, filename=path.name, file_type="pdf",
            parser_name=self.name, char_count=len(text),
            page_count=len(reader.pages),
        )


class DocxParser(BaseParser):
    name = "docx"

    @classmethod
    def accepts(cls) -> set[str]:
        return {".docx", ".doc"}

    def parse(self, path: Path) -> ParseResult:
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("python-docx is required to parse DOCX files") from exc
        doc = Document(str(path))
        blocks = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(blocks)
        return ParseResult(
            text=text, filename=path.name, file_type="docx",
            parser_name=self.name, char_count=len(text),
        )
