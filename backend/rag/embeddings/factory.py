"""Embedding provider factory — resolves at runtime."""

from __future__ import annotations

import os
import logging

from rag.core.base import BaseEmbeddingProvider
from rag.core.exceptions import EmbeddingError

from .hash_embedding import HashEmbeddingProvider
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_providers: dict[str, BaseEmbeddingProvider] = {}


def register_providers() -> None:
    _providers["hash"] = HashEmbeddingProvider()
    _providers["openai"] = OpenAICompatibleProvider()


def get_provider(name: str | None = None) -> BaseEmbeddingProvider:
    if not _providers:
        register_providers()

    provider_name = name or os.getenv("EMBEDDING_PROVIDER", "openai")

    if provider_name == "openai":
        provider = _providers["openai"]
        if not provider.is_configured:
            logger.warning(
                "[Embedding] OpenAI provider not configured (no API key); "
                "falling back to hash embedding for demo mode. "
                "Set EMBEDDING_API_KEY in .env for real embeddings."
            )
            return _providers["hash"]
        return provider

    provider = _providers.get(provider_name)
    if provider is None:
        logger.warning("Unknown embedding provider '%s'; using hash", provider_name)
        return _providers["hash"]
    return provider
