"""Parser migration — delegates to yuxi_rag.parsers for now.

Once the full migration is complete, these will be the canonical parsers.
"""

# Re-export from the existing yuxi_rag parsers for backward compatibility
import sys
from pathlib import Path

_rag_lab_dir = Path(__file__).resolve().parents[2] / "rag_lab"
if str(_rag_lab_dir) not in sys.path:
    sys.path.insert(0, str(_rag_lab_dir))

try:
    from yuxi_rag.parsers import (  # noqa: F401
        BaseParser, ParseResult, ParseError,
        TextParser, PdfParser, DocxParser,
        get_parser, parse_file, parse_files, supported_extensions,
        format_parse_result,
    )
except ImportError:  # pragma: no cover
    pass
