from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
RAG_LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DOCS_DIR = RAG_LAB_DIR / "data" / "docs"


@dataclass(slots=True)
class DocumentFile:
    path: Path
    source: str
    file_id: str
    extension: str


def _make_file_id(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    digest = hashlib.md5(rel.encode("utf-8")).hexdigest()[:10]
    stem = path.stem.replace(" ", "_")[:40]
    return f"{stem}_{digest}"


def load_documents(docs_dir: str | Path = DEFAULT_DOCS_DIR) -> list[DocumentFile]:
    root = Path(docs_dir).resolve()
    if not root.exists():
        return []

    files: list[DocumentFile] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            continue
        files.append(
            DocumentFile(
                path=path,
                source=path.relative_to(root).as_posix(),
                file_id=_make_file_id(path, root),
                extension=extension,
            )
        )
    return files
