from __future__ import annotations

import os
import sys
import time
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
RAG_LAB_DIR = THIS_FILE.parents[1]
BACKEND_DIR = RAG_LAB_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
for candidate in (RAG_LAB_DIR, BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _normalize_debug_env() -> None:
    raw = os.getenv("DEBUG", "")
    normalized = raw.strip().lower()
    if not normalized:
        os.environ["DEBUG"] = "false"
        return
    if normalized not in {"true", "false", "1", "0", "yes", "no", "y", "n"}:
        os.environ["DEBUG"] = "false"


_normalize_debug_env()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _ensure_ok(resp, step: str) -> None:
    if resp.status_code >= 400:
        raise RuntimeError(f"{step} failed: {resp.status_code} {resp.text}")


def _create_kb(client: TestClient) -> str:
    payload = {
        "name": f"smoke_kb_{int(time.time())}",
        "description": "smoke test",
    }
    resp = client.post("/api/v1/knowledge-bases", json=payload)
    _ensure_ok(resp, "create kb")
    data = resp.json()
    kb_id = data.get("id")
    if not kb_id:
        raise RuntimeError("create kb failed: missing id")
    return kb_id


def _create_session(client: TestClient, kb_id: str) -> str:
    resp = client.post("/api/v1/chat/sessions", json={"kb_id": kb_id, "title": "Smoke Test"})
    _ensure_ok(resp, "create session")
    data = resp.json()
    session_id = data.get("id")
    if not session_id:
        raise RuntimeError("create session failed: missing id")
    return session_id


def _upload_doc(client: TestClient, kb_id: str) -> str:
    content = (
        "RAG 是 Retrieval Augmented Generation。\n"
        "它通过检索相关文档，再结合生成模型给出回答。\n"
        "该流程包含文档解析、分块、向量化、检索与回答。\n"
    )
    files = {"files": ("smoke.txt", content.encode("utf-8"), "text/plain")}
    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/documents/upload", files=files)
    _ensure_ok(resp, "upload document")
    data = resp.json()
    if not isinstance(data, list) or not data:
        raise RuntimeError("upload document failed: empty response")
    doc_id = data[0].get("id")
    if not doc_id:
        raise RuntimeError("upload document failed: missing doc id")
    return doc_id


def _rebuild_index(client: TestClient, kb_id: str) -> dict:
    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/rebuild-index")
    _ensure_ok(resp, "rebuild index")
    data = resp.json()
    status = data.get("status")
    if status not in {"completed", "partial"}:
        raise RuntimeError(f"rebuild index failed: status={status}")
    if int(data.get("chunk_count") or 0) <= 0:
        raise RuntimeError(f"rebuild index failed: chunk_count={data.get('chunk_count')}")
    return data


def _query(client: TestClient, kb_id: str, session_id: str, engine: str) -> dict:
    payload = {"kb_id": kb_id, "session_id": session_id, "query": "RAG 的全称是什么？"}
    resp = client.post("/api/v1/chat/query", json=payload)
    _ensure_ok(resp, "query")
    data = resp.json()
    required_keys = ["answer", "sources"]
    if engine == "rag_lab":
        required_keys.extend(["contexts", "score", "metadata"])
    for key in required_keys:
        if key not in data:
            raise RuntimeError(f"query response missing {key}")
    if not isinstance(data.get("sources"), list):
        raise RuntimeError("query response sources is not list")
    return data


def _query_stream(client: TestClient, kb_id: str, session_id: str) -> str:
    payload = {"kb_id": kb_id, "session_id": session_id, "query": "RAG 的全称是什么？"}
    with client.stream("POST", "/api/v1/chat/query/stream", json=payload) as resp:
        _ensure_ok(resp, "query stream")
        body = b"".join(resp.iter_bytes()).decode("utf-8", errors="ignore")
    events: list[str] = []
    for line in body.splitlines():
        if line.startswith("event:"):
            events.append(line.split(":", 1)[1].strip())
    for required in ("chunk", "sources", "done"):
        if required not in events:
            raise RuntimeError(f"stream missing event {required}")
    return body


def main() -> None:
    engine = os.getenv("RAG_ENGINE", "rag_lab")
    with TestClient(app) as client:
        kb_id = _create_kb(client)
        session_id = _create_session(client, kb_id)
        doc_id = _upload_doc(client, kb_id)
        rebuild = _rebuild_index(client, kb_id)
        query = _query(client, kb_id, session_id, engine)
        _query_stream(client, kb_id, session_id)

    print(f"smoke ok: engine={engine} kb_id={kb_id} doc_id={doc_id}")
    print(f"rebuild status={rebuild.get('status')} chunk_count={rebuild.get('chunk_count')}")
    print(f"query answer_length={len(query.get('answer') or '')} sources={len(query.get('sources') or [])}")
    print("stream events ok")


if __name__ == "__main__":
    main()
