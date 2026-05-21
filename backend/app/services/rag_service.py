import logging
from typing import AsyncIterator
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.hybrid_search_service import HybridSearchService
from app.services.llm_service import llm_service
from app.services.chat_history_service import ChatHistoryService
from app.services.reranker_service import reranker_service, RerankerError

logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are a helpful assistant. You answer questions based ONLY on the provided document context.

=== STRICT RULES ===
1. You may ONLY use the context below to answer. Do NOT use any external knowledge, training data, or general world knowledge.
2. If the context does not contain enough information to answer, clearly state:
   "根据现有资料无法回答该问题" (The available documents do not contain enough information to answer this question).
   Then briefly explain what is missing. Do NOT fabricate an answer.
3. Every key factual claim — numbers, amounts, dates, procedures, policies, parameters — MUST be directly supported by at least one source in the context.
4. Do NOT invent any systems, processes, amounts, dates, parameters, or policies that are not explicitly present in the context.
5. When referencing information, cite the [Source: document_name] and section path (e.g. "第三章 > 第一节 > （一）").
6. If information is ambiguous or incomplete, say so rather than guessing.
7. Do NOT use markdown formatting for bold/italic in citations unless the source text itself uses it.

=== CONTEXT ===
{context}"""

# ── Low-confidence response templates ──────────────────────────────

_INSUFFICIENT_ANSWER = (
    "当前知识库中没有找到足够相关的资料，无法基于现有文档回答该问题。"
    "建议补充相关文档或换一种问法。"
)

_REASON_MESSAGES = {
    "no_results": "检索未返回任何结果",
    "insufficient_sources": "有效来源数量不足",
    "low_confidence": "最高相似度分数低于阈值",
    "no_relevant_sources": "无有效来源且配置不允许无资料回答",
}


class RAGService:
    def __init__(self):
        self.retrieval = RetrievalService()
        self.hybrid_search = HybridSearchService()
        self.history_service = ChatHistoryService()
        self.max_history_turns = settings.MAX_HISTORY_TURNS
        self.score_threshold = settings.SIMILARITY_SCORE_THRESHOLD
        self.min_source_count = settings.MIN_SOURCE_COUNT
        self.answer_without_source = settings.ANSWER_WITHOUT_SOURCE
        self.enable_reranker = settings.ENABLE_RERANKER
        self.reranker_top_k = settings.RERANKER_TOP_K
        self.reranker_top_n = settings.RERANKER_TOP_N
        self.enable_hybrid = settings.ENABLE_HYBRID_SEARCH

    # ── Confidence gating ──────────────────────────────────────────

    def _check_confidence(self, hits: list[dict]) -> dict:
        """
        Determine if we have enough confidence to call the LLM.

        When hybrid search is enabled, uses ``effective_score`` (which
        accounts for both vector and BM25 signals).  When disabled, uses
        the original ``raw_score``-based logic from Phase 2.
        """
        if not hits:
            return {
                "ok": False,
                "reason": "no_results",
                "top_similarity_score": 0.0,
            }

        if self.enable_hybrid:
            # Hybrid mode — use effective_score (higher = better)
            eff_threshold = 1.0 - self.score_threshold
            effective = [h for h in hits
                         if h.get("effective_score", h.get("similarity_score", 0.0)) >= eff_threshold]
            top_sim = max(h.get("effective_score", h.get("similarity_score", 0.0)) for h in hits)
        else:
            # Original Phase 2 logic — use raw_score (lower = better)
            effective = [h for h in hits
                         if h.get("raw_score", 1.0) <= self.score_threshold]
            top_sim = max(h.get("similarity_score", 0.0) for h in hits)

        if len(effective) < self.min_source_count:
            return {
                "ok": False,
                "reason": "insufficient_sources",
                "top_similarity_score": top_sim,
                "effective_count": len(effective),
                "min_required": self.min_source_count,
            }

        if not self.answer_without_source and len(effective) == 0:
            return {
                "ok": False,
                "reason": "no_relevant_sources",
                "top_similarity_score": top_sim,
            }

        return {"ok": True, "top_similarity_score": top_sim,
                "effective_count": len(effective)}

    def _build_insufficient_response(self, reason: str,
                                     top_similarity_score: float = 0.0) -> dict:
        return {
            "answer": _INSUFFICIENT_ANSWER,
            "sources": [],
            "confidence": "low",
            "reason": reason,
            "top_similarity_score": top_similarity_score,
            "threshold": self.score_threshold,
        }

    # ── Source & annotation helpers ─────────────────────────────────

    @staticmethod
    def _build_section_annotation(hit: dict) -> str:
        parts = []
        sp = hit.get("section_path")
        if sp:
            parts.append(sp)
        elif hit.get("section_title"):
            parts.append(hit["section_title"])
        page = hit.get("page")
        if page is not None:
            parts.append(f"第{page + 1}页")
        if parts:
            return f" ({' | '.join(parts)})"
        return ""

    @staticmethod
    def _build_source(hit: dict) -> dict:
        src = {
            "document_name": hit.get("document_name", ""),
            "chunk_index": hit.get("chunk_index", 0),
            "section_title": hit.get("section_title", ""),
            "section_path": hit.get("section_path", ""),
            "page": hit.get("page"),
            "score": hit.get("score", 0.0),
            "raw_score": hit.get("raw_score", hit.get("score", 0.0)),
            "similarity_score": hit.get("similarity_score", 0.0),
            "content": (hit.get("content", "") or "")[:300],
            "content_preview": (hit.get("content", "") or "")[:200],
        }
        if "rerank_score" in hit:
            src["rerank_score"] = hit["rerank_score"]
        if "rerank_rank" in hit:
            src["rerank_rank"] = hit["rerank_rank"]
        # Hybrid search fields (present only when ENABLE_HYBRID_SEARCH=true)
        if "retrieval_source" in hit:
            src["retrieval_source"] = hit["retrieval_source"]
        if "vector_score" in hit:
            src["vector_score"] = hit["vector_score"]
        if "bm25_score" in hit:
            src["bm25_score"] = hit["bm25_score"]
        if "bm25_score_norm" in hit:
            src["bm25_score_norm"] = hit["bm25_score_norm"]
        if "hybrid_score" in hit:
            src["hybrid_score"] = hit["hybrid_score"]
        if "effective_score" in hit:
            src["effective_score"] = hit["effective_score"]
        return src

    # ── Logging ─────────────────────────────────────────────────────

    def _log_rag(self, query: str, hits: list[dict], decision: dict) -> None:
        top_raw = min(h.get("raw_score", 1.0) for h in hits) if hits else 0.0
        top_sim = max(h.get("similarity_score", 0.0) for h in hits) if hits else 0.0
        eff = decision.get("effective_count", 0)

        if decision["ok"]:
            logger.info(
                "[RAG] query=\"%s\" hits=%d effective=%d "
                "top_raw=%.4f top_sim=%.4f threshold=%.2f → LLM",
                query[:100], len(hits), eff, top_raw, top_sim, self.score_threshold,
            )
        else:
            logger.warning(
                "[RAG] query=\"%s\" hits=%d effective=%d "
                "top_raw=%.4f top_sim=%.4f threshold=%.2f → REJECTED (%s)",
                query[:100], len(hits), eff, top_raw, top_sim,
                self.score_threshold, decision.get("reason", "unknown"),
            )

    # ── Reranker integration ──────────────────────────────────────────

    async def _apply_reranker_if_enabled(
        self, query: str, hits: list[dict]
    ) -> list[dict]:
        """Optionally re-rank *hits* and truncate to reranker_top_n.

        When the reranker is disabled, hits pass through unchanged.
        On failure, falls back to the original vector order (truncated).
        """
        if not self.enable_reranker:
            return hits

        recall_count = len(hits)
        logger.info(
            "[Reranker] enabled=true provider=%s model=%s recall_count=%d input_count=%d",
            settings.RERANKER_PROVIDER,
            settings.RERANKER_MODEL,
            recall_count,
            recall_count,
        )

        try:
            ranked = await reranker_service.rerank(query, hits)
        except RerankerError as exc:
            logger.warning(
                "[Reranker] fallback=true reason=\"%s\" — using vector order",
                exc,
            )
            return hits[: self.reranker_top_n]

        top_score = ranked[0]["rerank_score"] if ranked else 0.0
        logger.info(
            "[Reranker] success input_count=%d output_count=%d top_rerank_score=%.4f fallback=false",
            recall_count,
            len(ranked),
            top_score,
        )

        result = ranked[: self.reranker_top_n]
        logger.info("[Reranker] final_sources=%d", len(result))
        return result

    # ── Query (streaming) ───────────────────────────────────────────

    async def query_stream(self, kb_id: str, session_id: str,
                           query: str) -> AsyncIterator[dict]:
        history = await self.history_service.get_history(
            session_id, self.max_history_turns * 2)
        await self.history_service.add_message(session_id, "user", query)

        recall_k = self.reranker_top_k if self.enable_reranker else None
        if self.enable_hybrid:
            results = await self.hybrid_search.search(kb_id, query)
        else:
            results = await self.retrieval.search(kb_id, query, top_k=recall_k)

        # Reranker — re-rank then truncate to top_n (no-op when disabled)
        results = await self._apply_reranker_if_enabled(query, results)

        # Confidence gate — block before any LLM call
        decision = self._check_confidence(results)
        self._log_rag(query, results, decision)

        if not decision["ok"]:
            resp = self._build_insufficient_response(
                decision["reason"],
                decision.get("top_similarity_score", 0.0),
            )
            msg_id = await self.history_service.add_message(
                session_id, "assistant", resp["answer"], [])
            yield {"type": "sources", "sources": []}
            yield {"type": "done", "message_id": msg_id,
                   "confidence": "low", "reason": decision["reason"]}
            return

        # Build context from effective hits only (above threshold)
        if self.enable_hybrid:
            eff_threshold = 1.0 - self.score_threshold
            effective = [h for h in results
                         if h.get("effective_score", h.get("similarity_score", 0.0)) >= eff_threshold]
        else:
            effective = [h for h in results
                         if h.get("raw_score", 1.0) <= self.score_threshold]
        context_parts = []
        sources = []
        for hit in effective:
            section_annotation = self._build_section_annotation(hit)
            context_parts.append(
                f"[Source: {hit['document_name']}{section_annotation}]\n{hit['content']}"
            )
            sources.append(self._build_source(hit))

        context = "\n\n---\n\n".join(context_parts) if context_parts else \
            "No relevant documents found."
        system_prompt = SYSTEM_TEMPLATE.format(context=context)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(self.history_service.format_history_for_llm(history))
        messages.append(HumanMessage(content=query))

        full_answer = ""
        async for token in llm_service.stream(messages):
            if token:
                full_answer += token
                yield {"type": "chunk", "text": token}

        msg_id = await self.history_service.add_message(
            session_id, "assistant", full_answer, sources)
        yield {"type": "sources", "sources": sources}
        yield {"type": "done", "message_id": msg_id,
               "top_similarity_score": decision.get("top_similarity_score", 0.0),
               "threshold": self.score_threshold}

    # ── Query (non-streaming) ───────────────────────────────────────

    async def query(self, kb_id: str, session_id: str, query: str) -> dict:
        history = await self.history_service.get_history(
            session_id, self.max_history_turns * 2)
        await self.history_service.add_message(session_id, "user", query)

        recall_k = self.reranker_top_k if self.enable_reranker else None
        if self.enable_hybrid:
            results = await self.hybrid_search.search(kb_id, query)
        else:
            results = await self.retrieval.search(kb_id, query, top_k=recall_k)

        # Reranker — re-rank then truncate to top_n (no-op when disabled)
        results = await self._apply_reranker_if_enabled(query, results)

        # Confidence gate
        decision = self._check_confidence(results)
        self._log_rag(query, results, decision)

        if not decision["ok"]:
            resp = self._build_insufficient_response(
                decision["reason"],
                decision.get("top_similarity_score", 0.0),
            )
            msg_id = await self.history_service.add_message(
                session_id, "assistant", resp["answer"], [])
            resp["message_id"] = msg_id
            return resp

        # Build context from effective hits only (above threshold)
        if self.enable_hybrid:
            eff_threshold = 1.0 - self.score_threshold
            effective = [h for h in results
                         if h.get("effective_score", h.get("similarity_score", 0.0)) >= eff_threshold]
        else:
            effective = [h for h in results
                         if h.get("raw_score", 1.0) <= self.score_threshold]
        context_parts = []
        sources = []
        for hit in effective:
            section_annotation = self._build_section_annotation(hit)
            context_parts.append(
                f"[Source: {hit['document_name']}{section_annotation}]\n{hit['content']}"
            )
            sources.append(self._build_source(hit))

        context = "\n\n---\n\n".join(context_parts) if context_parts else \
            "No relevant documents found."
        system_prompt = SYSTEM_TEMPLATE.format(context=context)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(self.history_service.format_history_for_llm(history))
        messages.append(HumanMessage(content=query))

        answer = await llm_service.generate(messages)
        msg_id = await self.history_service.add_message(
            session_id, "assistant", answer, sources)
        return {
            "answer": answer,
            "sources": sources,
            "message_id": msg_id,
            "top_similarity_score": decision.get("top_similarity_score", 0.0),
            "threshold": self.score_threshold,
        }
