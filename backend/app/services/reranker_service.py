import asyncio
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class RerankerError(Exception):
    """Raised when reranking fails, so the caller can fallback to vector results."""


class RerankerService:
    """Re-rank candidate chunks using DashScope gte-rerank-v2.

    Input / output are plain dicts — no LangChain Document dependency.
    """

    def __init__(self):
        self.provider = settings.RERANKER_PROVIDER
        self.model = settings.RERANKER_MODEL
        self.api_key = settings.DASHSCOPE_API_KEY or settings.EMBEDDING_API_KEY
        self.timeout = settings.RERANKER_TIMEOUT
        self.top_n = settings.RERANKER_TOP_N
        self.score_threshold = settings.RERANKER_SCORE_THRESHOLD
        self._enabled = settings.ENABLE_RERANKER

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def rerank(self, query: str, sources: list[dict]) -> list[dict]:
        """Re-rank *sources* by relevance to *query*.

        Returns a new list ordered by relevance_score (descending), with
        ``rerank_score`` and ``rerank_rank`` attached to each item.
        """
        if not sources:
            return []

        if not self.api_key:
            raise RerankerError("DASHSCOPE_API_KEY is not configured")

        documents = [s.get("content", "") for s in sources]

        try:
            import dashscope
        except ImportError:
            raise RerankerError("dashscope package is not installed")

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: dashscope.TextReRank.call(
                    model=self.model,
                    query=query,
                    documents=documents,
                    top_n=self.top_n,
                    return_documents=False,
                    api_key=self.api_key,
                    timeout=self.timeout,
                ),
            )
        except Exception as exc:
            raise RerankerError(f"DashScope rerank API call failed: {exc}") from exc

        if response.status_code != 200:
            raise RerankerError(
                f"DashScope rerank returned status {response.status_code}: "
                f"{response.message}"
            )

        results = response.output.results if response.output else []

        if not results:
            logger.warning(
                "[Reranker] API returned no results — falling back to vector order"
            )
            raise RerankerError("Reranker returned empty results")

        ranked: list[dict] = []
        for rank, item in enumerate(results):
            idx = item.index
            score = item.relevance_score

            if self.score_threshold > 0 and score < self.score_threshold:
                continue

            src = dict(sources[idx])
            src["rerank_score"] = round(score, 4)
            src["rerank_rank"] = rank
            ranked.append(src)

        return ranked


reranker_service = RerankerService()
