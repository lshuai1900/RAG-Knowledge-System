import os
import json
import pickle
import logging
import asyncio

import jieba
from rank_bm25 import BM25Okapi

# Common Chinese enterprise document terms that jieba may split incorrectly
_CUSTOM_WORDS = [
    "年假", "病假", "事假", "婚假", "产假", "陪产假", "哺乳期",
    "考勤", "全勤", "加班费", "报销流程", "差旅报销", "招待费",
    "社保", "公积金", "竞业限制", "知识产权", "商业秘密",
]
for _w in _CUSTOM_WORDS:
    jieba.add_word(_w)

from app.config import settings
from app.db.milvus_client import milvus_client

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Chinese-aware tokenizer that preserves English words, numbers, and codes.

    Uses jieba for Chinese segmentation. English words and numbers pass through
    as-is. Model numbers like HR-2024-01, P2G, CCS, KB001 are preserved as
    individual tokens that can be matched.
    """
    if not text:
        return []
    tokens = jieba.lcut(text)
    return [t.strip() for t in tokens if t.strip()]


class BM25Service:
    """Per-kb BM25 index: build, persist, search, delete."""

    def __init__(self):
        self.index_path = settings.BM25_INDEX_PATH
        self.score_threshold = settings.BM25_SCORE_THRESHOLD

    # ── Paths ────────────────────────────────────────────────────────

    def _kb_dir(self, kb_id: str) -> str:
        return os.path.join(self.index_path, kb_id)

    def _index_file(self, kb_id: str) -> str:
        return os.path.join(self._kb_dir(kb_id), "index.pkl")

    def _chunks_file(self, kb_id: str) -> str:
        return os.path.join(self._kb_dir(kb_id), "chunks.json")

    # ── Build ────────────────────────────────────────────────────────

    async def build_index(self, kb_id: str) -> int:
        """Build (or rebuild) BM25 index for *kb_id* from Milvus data.

        Returns the number of chunks indexed.
        """
        all_chunks = await milvus_client.get_all_chunks(kb_id)

        if not all_chunks:
            self.delete_index(kb_id)
            logger.info("[BM25] kb=%s — empty corpus, index cleared", kb_id)
            return 0

        tokenized_corpus = [_tokenize(chunk["content"]) for chunk in all_chunks]

        bm25 = BM25Okapi(tokenized_corpus)

        kb_dir = self._kb_dir(kb_id)
        os.makedirs(kb_dir, exist_ok=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._save_index_sync,
            kb_id,
            bm25,
            tokenized_corpus,
            all_chunks,
        )

        logger.info(
            "[BM25] kb=%s index built chunk_count=%d",
            kb_id,
            len(all_chunks),
        )
        return len(all_chunks)

    def _save_index_sync(self, kb_id, bm25, tokenized_corpus, chunks):
        """Serialize BM25 index and metadata to disk (runs in thread pool)."""
        with open(self._index_file(kb_id), "wb") as f:
            pickle.dump(
                {
                    "bm25": bm25,
                    "tokenized_corpus": tokenized_corpus,
                    "chunk_count": len(chunks),
                    "kb_id": kb_id,
                },
                f,
            )

        chunk_records = []
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_records.append({
                "milvus_id": chunk.get("id"),
                "kb_id": kb_id,
                "doc_id": chunk.get("doc_id", ""),
                "document_name": chunk.get("document_name", ""),
                "chunk_id": f"{chunk.get('doc_id', '')}_{chunk.get('chunk_index', 0)}",
                "chunk_index": chunk.get("chunk_index", 0),
                "section_title": chunk.get("section_title", ""),
                "section_path": chunk.get("section_path", ""),
                "page": chunk.get("page"),
                "content": content,
                "content_preview": content[:200],
            })

        with open(self._chunks_file(kb_id), "w", encoding="utf-8") as f:
            json.dump(chunk_records, f, ensure_ascii=False, indent=2)

    # ── Search ───────────────────────────────────────────────────────

    async def search(self, kb_id: str, query: str, top_k: int) -> list[dict]:
        """Search the BM25 index for *kb_id*.

        Returns a list of hit dicts with normalized bm25 scores.
        Returns empty list if the index does not exist or is empty.
        """
        idx_file = self._index_file(kb_id)
        chunks_file = self._chunks_file(kb_id)

        if not os.path.exists(idx_file) or not os.path.exists(chunks_file):
            logger.warning(
                "[BM25] kb=%s index not found at %s — returning empty",
                kb_id,
                idx_file,
            )
            return []

        loop = asyncio.get_event_loop()

        bm25, tokenized_corpus = await loop.run_in_executor(
            None, self._load_index_sync, kb_id)
        chunks = await loop.run_in_executor(
            None, self._load_chunks_sync, kb_id)

        if bm25 is None or not chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        raw_scores = bm25.get_scores(query_tokens)

        indexed = []
        for i, score in enumerate(raw_scores):
            if i >= len(chunks):
                break
            indexed.append((i, float(score)))

        if not indexed:
            return []

        scores_arr = [s for _, s in indexed]
        min_s = min(scores_arr)
        max_s = max(scores_arr)

        # If the best raw BM25 score is still very low, all matches are noise.
        # This prevents min-max normalization from inflating near-zero scores
        # to 1.0 for out-of-domain queries that match only generic stop-words.
        min_raw = getattr(settings, "BM25_MIN_RAW_SCORE", 0.3)
        if max_s < min_raw:
            return []

        results = []
        for i, raw_score in indexed:
            chunk = chunks[i]

            if max_s > min_s:
                bm25_norm = (raw_score - min_s) / (max_s - min_s)
            else:
                bm25_norm = 1.0

            if bm25_norm < self.score_threshold:
                continue

            results.append({
                "id": chunk.get("milvus_id", i),
                "content": chunk.get("content", ""),
                "document_name": chunk.get("document_name", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "chunk_id": chunk.get("chunk_id", ""),
                "doc_id": chunk.get("doc_id", ""),
                "section_title": chunk.get("section_title", ""),
                "section_path": chunk.get("section_path", ""),
                "page": chunk.get("page"),
                "score": round(raw_score, 4),
                "raw_score": 0.0,
                "similarity_score": round(bm25_norm, 4),
                "bm25_score": round(raw_score, 4),
                "bm25_score_norm": round(bm25_norm, 4),
                "vector_score": None,
                "hybrid_score": round(bm25_norm, 4),
                "effective_score": round(bm25_norm, 4),
                "retrieval_source": "bm25",
            })

        results.sort(key=lambda x: x["bm25_score_norm"], reverse=True)
        return results[:top_k]

    # ── Load helpers (sync, run in thread pool) ──────────────────────

    def _load_index_sync(self, kb_id: str):
        try:
            with open(self._index_file(kb_id), "rb") as f:
                data = pickle.load(f)
            return data["bm25"], data.get("tokenized_corpus", [])
        except Exception as exc:
            logger.error("[BM25] Failed to load index for kb=%s: %s", kb_id, exc)
            return None, []

    def _load_chunks_sync(self, kb_id: str) -> list[dict]:
        try:
            with open(self._chunks_file(kb_id), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("[BM25] Failed to load chunks for kb=%s: %s", kb_id, exc)
            return []

    # ── Delete ───────────────────────────────────────────────────────

    async def delete_index(self, kb_id: str) -> None:
        """Remove BM25 index files for *kb_id*."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_index_sync, kb_id)

    def _delete_index_sync(self, kb_id: str):
        import shutil
        kb_dir = self._kb_dir(kb_id)
        if os.path.isdir(kb_dir):
            shutil.rmtree(kb_dir)
            logger.info("[BM25] kb=%s index deleted", kb_id)

    async def delete_document_chunks(self, kb_id: str, doc_id: str) -> int:
        """Remove all chunks belonging to *doc_id* from the BM25 index.

        Loads the existing index, filters out the target document's chunks,
        rebuilds the BM25 model from the remaining corpus, and persists.

        Returns the number of chunks removed.  Returns 0 if the index does
        not exist (idempotent).
        """
        idx_file = self._index_file(kb_id)
        chunks_file = self._chunks_file(kb_id)

        if not os.path.exists(idx_file) or not os.path.exists(chunks_file):
            logger.info(
                "[BM25] kb=%s doc=%s — index not found, skip delete",
                kb_id, doc_id,
            )
            return 0

        loop = asyncio.get_event_loop()
        all_chunks = await loop.run_in_executor(
            None, self._load_chunks_sync, kb_id)

        original_count = len(all_chunks)
        kept_chunks = [
            c for c in all_chunks
            if c.get("doc_id") != doc_id
        ]
        removed_count = original_count - len(kept_chunks)

        if removed_count == 0:
            logger.info(
                "[BM25] kb=%s doc=%s — no chunks found in index",
                kb_id, doc_id,
            )
            return 0

        if not kept_chunks:
            # No chunks left — remove the index entirely
            await loop.run_in_executor(None, self._delete_index_sync, kb_id)
            logger.info(
                "[BM25] kb=%s doc=%s removed_count=%d — index empty, deleted",
                kb_id, doc_id, removed_count,
            )
            return removed_count

        # Rebuild BM25 from remaining chunks
        tokenized_corpus = [_tokenize(c["content"]) for c in kept_chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        kb_dir = self._kb_dir(kb_id)
        os.makedirs(kb_dir, exist_ok=True)
        await loop.run_in_executor(
            None,
            self._save_index_sync,
            kb_id,
            bm25,
            tokenized_corpus,
            kept_chunks,
        )

        logger.info(
            "[BM25] kb=%s doc=%s removed_count=%d remaining=%d",
            kb_id, doc_id, removed_count, len(kept_chunks),
        )
        return removed_count

    async def index_exists(self, kb_id: str) -> bool:
        return os.path.exists(self._index_file(kb_id))

    async def get_chunk_count(self, kb_id: str) -> int:
        """Return the number of chunks currently in the BM25 index."""
        chunks_file = self._chunks_file(kb_id)
        if not os.path.exists(chunks_file):
            return 0
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None, self._load_chunks_sync, kb_id)
        return len(chunks)


bm25_service = BM25Service()
