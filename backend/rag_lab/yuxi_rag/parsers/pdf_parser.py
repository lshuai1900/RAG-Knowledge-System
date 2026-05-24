from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParseResult, format_parse_result


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
        pages: list[str] = []
        page_count = len(reader.pages)
        for page in reader.pages:
            extracted = page.extract_text() or ""
            pages.append(extracted)

        return format_parse_result(
            self.name,
            "\n\n".join(pages),
            filename=path.name,
            file_type="pdf",
            page_count=page_count,
        )
