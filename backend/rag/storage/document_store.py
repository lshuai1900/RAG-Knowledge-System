"""Document metadata store — JSON-backed for the Yuxi-style RAG module.

All document read/write goes through this module.
Business logic should NOT open JSON files directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag.core.schemas import DocumentRecord


class DocumentStore:
    """JSON-backed document metadata store."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _docs_dir(self, kb_id: str) -> Path:
        d = self.data_dir / kb_id / "docs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, kb_id: str, record: DocumentRecord) -> None:
        path = self._docs_dir(kb_id) / f"{record.doc_id}.json"
        path.write_text(json.dumps(_dataclass_to_dict(record),
                                    ensure_ascii=False, indent=2))

    def get(self, kb_id: str, doc_id: str) -> DocumentRecord | None:
        path = self._docs_dir(kb_id) / f"{doc_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return DocumentRecord(**data)

    def list(self, kb_id: str) -> list[DocumentRecord]:
        d = self._docs_dir(kb_id)
        if not d.exists():
            return []
        records = []
        for f in sorted(d.glob("*.json")):
            data = json.loads(f.read_text())
            records.append(DocumentRecord(**data))
        return records

    def delete(self, kb_id: str, doc_id: str) -> None:
        path = self._docs_dir(kb_id) / f"{doc_id}.json"
        if path.exists():
            path.unlink()


class ChunkStore:
    """JSON-backed chunk store."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _chunks_dir(self, kb_id: str) -> Path:
        d = self.data_dir / kb_id / "chunks"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, kb_id: str, doc_id: str, chunks: list) -> None:
        path = self._chunks_dir(kb_id) / f"{doc_id}.json"
        path.write_text(json.dumps(
            [c.to_dict() if hasattr(c, "to_dict") else c for c in chunks],
            ensure_ascii=False, indent=2))

    def load(self, kb_id: str, doc_ids: list[str] | None = None) -> list:
        from rag.core.schemas import ChunkRecord
        d = self._chunks_dir(kb_id)
        if not d.exists():
            return []
        all_chunks = []
        for f in sorted(d.glob("*.json")):
            if doc_ids and f.stem not in doc_ids:
                continue
            for row in json.loads(f.read_text()):
                all_chunks.append(ChunkRecord(**row))
        return all_chunks

    def delete(self, kb_id: str, doc_id: str) -> None:
        path = self._chunks_dir(kb_id) / f"{doc_id}.json"
        if path.exists():
            path.unlink()


class VectorStore:
    """Numpy-backed vector store."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _kb_dir(self, kb_id: str) -> Path:
        d = self.data_dir / kb_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, kb_id: str, embeddings: list, chunk_ids: list[str],
             dimension: int, model: str, provider: str) -> None:
        import numpy as np
        arr = np.array(embeddings, dtype=np.float32)
        np.save(str(self._kb_dir(kb_id) / "embeddings.npy"), arr)
        meta = {
            "chunk_ids": chunk_ids, "dimension": dimension,
            "model": model, "provider": provider,
            "chunk_count": len(chunk_ids),
            "built_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
        }
        (self._kb_dir(kb_id) / "index_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2))

    def load(self, kb_id: str) -> tuple:
        import numpy as np
        emb_path = self._kb_dir(kb_id) / "embeddings.npy"
        meta_path = self._kb_dir(kb_id) / "index_meta.json"
        if not emb_path.exists() or not meta_path.exists():
            return None, None
        return np.load(str(emb_path)), json.loads(meta_path.read_text())

    def exists(self, kb_id: str) -> bool:
        return (self._kb_dir(kb_id) / "embeddings.npy").exists()

    def delete(self, kb_id: str) -> None:
        for name in ("embeddings.npy", "index_meta.json"):
            p = self._kb_dir(kb_id) / name
            if p.exists():
                p.unlink()


def _dataclass_to_dict(obj: Any) -> dict:
    try:
        import dataclasses
        return dataclasses.asdict(obj)
    except Exception:
        return obj.__dict__ if hasattr(obj, "__dict__") else dict(obj)
