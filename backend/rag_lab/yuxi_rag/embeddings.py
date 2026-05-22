from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
for candidate in (BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


@dataclass(slots=True)
class EmbeddingConfig:
    model: str
    api_key: str
    base_url: str | None
    batch_size: int = 10


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_local_env() -> None:
    _load_dotenv_file(PROJECT_ROOT / ".env")
    _load_dotenv_file(BACKEND_DIR / ".env")


def get_embedding_config() -> EmbeddingConfig:
    load_local_env()
    settings = None
    try:
        from app.config import settings as app_settings
        settings = app_settings
    except Exception:
        settings = None

    model = os.getenv("EMBED_MODEL") or os.getenv("EMBEDDING_MODEL_NAME")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("EMBEDDING_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("EMBEDDING_API_BASE")

    if settings is not None:
        model = model or settings.EMBEDDING_MODEL_NAME
        api_key = api_key or settings.EMBEDDING_API_KEY
        base_url = base_url or settings.EMBEDDING_API_BASE

    model = model or "text-embedding-v4"
    if not api_key:
        raise RuntimeError("Embedding API key is not configured. Set LLM_API_KEY or EMBEDDING_API_KEY in .env.")

    return EmbeddingConfig(model=model, api_key=api_key, base_url=base_url, batch_size=10)


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or get_embedding_config()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - dependency issue
                raise RuntimeError("openai package is required for embeddings") from exc
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def embed_query(self, text: str) -> list[float]:
        client = self._get_client()
        response = await client.embeddings.create(model=self.config.model, input=text)
        return response.data[0].embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            response = await client.embeddings.create(model=self.config.model, input=batch)
            embeddings.extend(item.embedding for item in response.data)
        return embeddings


def embed_documents_sync(texts: list[str], config: EmbeddingConfig | None = None) -> list[list[float]]:
    return asyncio.run(EmbeddingClient(config).embed_documents(texts))


def embed_query_sync(text: str, config: EmbeddingConfig | None = None) -> list[float]:
    return asyncio.run(EmbeddingClient(config).embed_query(text))
