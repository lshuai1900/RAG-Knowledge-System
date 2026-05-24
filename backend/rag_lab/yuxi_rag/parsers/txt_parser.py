from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParseResult, format_parse_result


class TextParser(BaseParser):
    name = "text"

    @classmethod
    def accepts(cls) -> set[str]:
        return {".txt", ".md", ".markdown"}

    def parse(self, path: Path) -> ParseResult:
        text = self._read_file(path)
        return format_parse_result(
            self.name,
            text,
            filename=path.name,
            file_type=path.suffix.lower().lstrip("."),
        )

    @staticmethod
    def _read_file(path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="ignore")
