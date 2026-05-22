from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .embeddings import BACKEND_DIR, PROJECT_ROOT, load_local_env
except ImportError:  # pragma: no cover - direct script fallback
    from embeddings import BACKEND_DIR, PROJECT_ROOT, load_local_env

for candidate in (BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

SYSTEM_PROMPT = """你是 Yuxi-RAG 实验模块的问答助手。请只根据给定 context 回答问题。
如果 context 中没有足够信息，请回答“根据现有资料无法回答该问题”，不要编造。
回答中尽量引用来源文件名。"""


@dataclass(slots=True)
class ChatConfig:
    model: str
    api_key: str
    base_url: str | None
    temperature: float = 0.1
    max_tokens: int = 2048


def get_chat_config() -> ChatConfig:
    load_local_env()
    settings = None
    try:
        from app.config import settings as app_settings
        settings = app_settings
    except Exception:
        settings = None

    model = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL_NAME")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_API_BASE")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    if settings is not None:
        model = model or settings.DEEPSEEK_MODEL_NAME
        api_key = api_key or settings.DEEPSEEK_API_KEY
        base_url = base_url or settings.DEEPSEEK_API_BASE
        temperature = float(os.getenv("LLM_TEMPERATURE", settings.LLM_TEMPERATURE))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", settings.LLM_MAX_TOKENS))

    model = model or "deepseek-chat"
    if not api_key:
        raise RuntimeError("Chat API key is not configured. Set LLM_API_KEY or DEEPSEEK_API_KEY in .env.")
    return ChatConfig(model=model, api_key=api_key, base_url=base_url, temperature=temperature, max_tokens=max_tokens)


def build_context(results: list[dict[str, Any]]) -> tuple[str, list[str], list[dict[str, Any]]]:
    contexts: list[str] = []
    sources: list[dict[str, Any]] = []
    for idx, result in enumerate(results, start=1):
        metadata = result.get("metadata") or {}
        source = metadata.get("source", "")
        page = metadata.get("page")
        page_text = f", page={page + 1}" if isinstance(page, int) else ""
        chunk_text = result.get("chunk_text", "")
        contexts.append(f"[Source: {source}{page_text}, chunk={metadata.get('chunk_index', idx - 1)}]\n{chunk_text}")
        source_row = {
            "source": source,
            "chunk_id": result.get("chunk_id"),
            "chunk_index": metadata.get("chunk_index"),
            "score": result.get("score"),
            "page": page,
            "content": chunk_text[:500],
            "metadata": metadata,
        }
        if "rerank_score" in result:
            source_row["rerank_score"] = result.get("rerank_score")
        sources.append(source_row)
    return "\n\n---\n\n".join(contexts), contexts, sources


class AnswerGenerator:
    def __init__(self, config: ChatConfig | None = None):
        self.config = config or get_chat_config()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - dependency issue
                raise RuntimeError("openai package is required for chat generation") from exc
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def generate(self, question: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        context, contexts, sources = build_context(results)
        if not context.strip():
            return {
                "answer": "根据现有资料无法回答该问题。",
                "contexts": [],
                "sources": [],
            }

        user_prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\n请基于 Context 用中文回答，并给出来源。"
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        answer = response.choices[0].message.content or ""
        return {
            "answer": answer,
            "contexts": contexts,
            "sources": sources,
        }
