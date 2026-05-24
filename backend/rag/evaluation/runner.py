"""Minimal evaluation runner — generates basic eval reports.

Full Ragas evaluation (faithfulness, answer_relevancy, context_precision,
context_recall) can be added later by extending this module.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_evaluation(kb_id: str, data_dir: Path,
                   dataset: list[dict] | None = None,
                   rag_service=None) -> dict[str, Any]:
    """Run minimal evaluation against *kb_id*.

    If *rag_service* is provided, each question is queried against the KB.
    Otherwise placeholder results are returned with a note about Ragas.
    """
    questions = dataset or _default_questions()

    report_dir = data_dir / "eval_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for q in questions:
        answer = ""
        contexts: list[str] = []
        sources: list[dict] = []
        error = None

        if rag_service:
            try:
                import asyncio
                resp = asyncio.run(
                    rag_service.query(kb_id, q.get("question", "")))
                answer = resp.get("answer", "")
                sources = resp.get("sources", [])
                contexts = [s.get("content", "") for s in sources]
            except Exception as exc:
                error = str(exc)

        results.append({
            "id": q.get("id"), "question": q.get("question"),
            "ground_truth": q.get("ground_truth", ""),
            "answer": answer, "contexts": contexts, "sources": sources,
            "metrics": {"hit_at_k": None, "recall_at_k": None, "mrr": None},
            "error": error,
        })

    report = {
        "run_name": f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kb_id": kb_id,
        "total_questions": len(results),
        "summary": {
            "hit_at_k": None, "recall_at_k": None, "mrr": None,
            "faithfulness": None, "answer_relevancy": None,
            "context_precision": None, "context_recall": None,
        },
        "results": results,
        "ragas_error": (
            "Ragas disabled — install ragas package and configure LLM_API_KEY "
            "for full evaluation metrics (faithfulness, answer_relevancy, "
            "context_precision, context_recall)."),
    }

    report_file = report_dir / "latest_eval.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    logger.info("Evaluation report saved to %s", report_file)
    return report


def _default_questions() -> list[dict]:
    return [
        {"id": "q1", "question": "系统支持哪些分块策略？",
         "ground_truth": "recursive, markdown_header, sentence_window, paragraph, auto"},
        {"id": "q2", "question": "检索流程包含哪些步骤？",
         "ground_truth": "Dense Retrieval → Sparse Retrieval → Fusion → Rerank → Answer"},
    ]
