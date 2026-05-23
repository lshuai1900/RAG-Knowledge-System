from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

THIS_FILE = Path(__file__).resolve()
RAG_LAB_DIR = THIS_FILE.parents[1]
BACKEND_DIR = RAG_LAB_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
for candidate in (RAG_LAB_DIR, BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from yuxi_rag import pipeline  # noqa: E402


BASE_METRICS = ["hit_at_k", "recall_at_k", "mrr", "keyword_hit"]
RAGAS_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if hasattr(value, "item"):
            value = value.item()
        num = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return round(num, 6)


def _mean(values: list[Any]) -> float | None:
    nums = [_safe_float(v) for v in values]
    nums = [v for v in nums if v is not None]
    if not nums:
        return None
    return round(statistics.fmean(nums), 6)


def _read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str | Path, payload: dict) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _normalize_questions(raw: Any, limit: int | None) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("questions file must contain a JSON array")
    questions: list[dict[str, Any]] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        q = dict(item)
        q.setdefault("id", f"q{idx:03d}")
        q.setdefault("question", "")
        q.setdefault("ground_truth", "")
        q.setdefault("expected_keywords", [])
        q.setdefault("expected_source", "")
        if not q.get("expected_source") and q.get("expected_sources"):
            q["expected_source"] = q.get("expected_sources")[0] if q.get("expected_sources") else ""
        questions.append(q)
    if limit is not None and limit > 0:
        return questions[:limit]
    return questions


def _source_name(source: dict[str, Any]) -> str:
    return str(source.get("source") or source.get("document_name") or source.get("filename") or "")


def _source_content(source: dict[str, Any]) -> str:
    return str(source.get("content") or source.get("chunk_text") or "")


def _source_matches_expected(source_name: str, expected_name: str) -> bool:
    if not source_name or not expected_name:
        return False
    src = source_name.lower()
    exp = expected_name.lower()
    src_base = os.path.basename(src)
    exp_base = os.path.basename(exp)
    return src == exp or src_base == exp_base or exp in src or exp_base in src_base or src_base in exp_base


def _find_expected_rank(sources: list[dict[str, Any]], expected_source: str) -> int | None:
    if not expected_source:
        return None
    for idx, src in enumerate(sources, start=1):
        name = _source_name(src)
        if _source_matches_expected(name, expected_source):
            return idx
    return None


def _keyword_hit(answer: str, contexts: list[str], expected_keywords: list[str]) -> bool:
    if not expected_keywords:
        return True
    haystack = f"{answer}\n" + "\n".join(contexts)
    haystack_lower = haystack.lower()
    return any(str(keyword).lower() in haystack_lower for keyword in expected_keywords if keyword)


def _extract_contexts(sources: list[dict[str, Any]]) -> list[str]:
    contexts: list[str] = []
    for src in sources:
        content = _source_content(src).strip()
        if content:
            contexts.append(content)
    return contexts


def _build_result(question: dict[str, Any], rag_output: dict[str, Any], top_k: int) -> dict[str, Any]:
    sources = rag_output.get("sources") or []
    contexts = rag_output.get("contexts") or _extract_contexts(sources)
    expected_source = question.get("expected_source") or ""
    rank = _find_expected_rank(sources[:top_k], expected_source)
    expected_source_hit = rank is not None if expected_source else True
    recall = 1.0 if expected_source_hit else 0.0
    return {
        "id": question.get("id"),
        "question": question.get("question"),
        "ground_truth": question.get("ground_truth", ""),
        "answer": rag_output.get("answer", ""),
        "sources": sources,
        "contexts": contexts,
        "expected_source": expected_source,
        "expected_keywords": question.get("expected_keywords") or [],
        "expected_source_hit": expected_source_hit,
        "keyword_hit": _keyword_hit(rag_output.get("answer", ""), contexts, question.get("expected_keywords") or []),
        "rank": rank,
        "metrics": {
            "hit_at_k": 1.0 if expected_source_hit else 0.0,
            "recall_at_k": round(recall, 6),
            "mrr": round(1.0 / rank, 6) if rank else 0.0,
        },
        "error": None,
    }


def _build_error_result(question: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        "id": question.get("id"),
        "question": question.get("question"),
        "ground_truth": question.get("ground_truth", ""),
        "answer": "",
        "sources": [],
        "contexts": [],
        "expected_source": question.get("expected_source") or "",
        "expected_keywords": question.get("expected_keywords") or [],
        "expected_source_hit": False,
        "keyword_hit": False,
        "rank": None,
        "metrics": {"hit_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0},
        "error": f"{type(error).__name__}: {error}",
    }


def _load_ragas_metrics() -> tuple[list[Any], list[str]]:
    from ragas import metrics as ragas_metrics  # type: ignore

    loaded: list[Any] = []
    names: list[str] = []
    for name in RAGAS_METRICS:
        metric = getattr(ragas_metrics, name, None)
        if metric is None and name == "answer_relevancy":
            metric = getattr(ragas_metrics, "response_relevancy", None)
            if metric is not None:
                names.append("response_relevancy")
        elif metric is not None:
            names.append(name)
        if metric is not None:
            loaded.append(metric)
    return loaded, names


def _make_ragas_dataset(results: list[dict[str, Any]]) -> Any:
    from datasets import Dataset  # type: ignore

    rows = []
    for result in results:
        rows.append({
            "question": result.get("question") or "",
            "answer": result.get("answer") or "",
            "contexts": result.get("contexts") or [],
            "ground_truth": result.get("ground_truth") or "",
            "user_input": result.get("question") or "",
            "response": result.get("answer") or "",
            "retrieved_contexts": result.get("contexts") or [],
            "reference": result.get("ground_truth") or "",
        })
    return Dataset.from_list(rows)


def _ragas_scores_to_rows(score: Any) -> list[dict[str, Any]]:
    if hasattr(score, "to_pandas"):
        return score.to_pandas().to_dict(orient="records")
    if isinstance(score, dict):
        row_count = max((len(v) for v in score.values() if isinstance(v, list)), default=0)
        if row_count == 0:
            return [dict(score)]
        return [
            {key: value[i] if isinstance(value, list) and i < len(value) else value for key, value in score.items()}
            for i in range(row_count)
        ]
    return []


async def _run_ragas(results: list[dict[str, Any]]) -> str | None:
    rows_for_ragas = [r for r in results if not r.get("error") and r.get("answer")]
    if not rows_for_ragas:
        return "No successful answered rows available for Ragas evaluation"

    try:
        from ragas import evaluate  # type: ignore
    except Exception as exc:
        return f"Ragas import failed: {type(exc).__name__}: {exc}"

    try:
        metrics, metric_names = _load_ragas_metrics()
        if not metrics:
            return "No compatible Ragas metrics found in installed ragas version"
        dataset = _make_ragas_dataset(rows_for_ragas)
        score = await asyncio.to_thread(lambda: evaluate(dataset, metrics=metrics))
        ragas_rows = _ragas_scores_to_rows(score)
        for result, ragas_row in zip(rows_for_ragas, ragas_rows):
            metrics_dict = result.setdefault("metrics", {})
            for key in RAGAS_METRICS + metric_names:
                if key in ragas_row:
                    normalized_key = "answer_relevancy" if key == "response_relevancy" else key
                    value = _safe_float(ragas_row.get(key))
                    if value is not None:
                        metrics_dict[normalized_key] = value
        return None
    except Exception as exc:
        return f"Ragas evaluation failed: {type(exc).__name__}: {exc}"


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {key: None for key in BASE_METRICS + RAGAS_METRICS}
    summary["hit_at_k"] = _mean([r.get("metrics", {}).get("hit_at_k") for r in results]) or 0.0
    summary["recall_at_k"] = _mean([r.get("metrics", {}).get("recall_at_k") for r in results]) or 0.0
    summary["mrr"] = _mean([r.get("metrics", {}).get("mrr") for r in results]) or 0.0
    summary["keyword_hit"] = _mean([1.0 if r.get("keyword_hit") else 0.0 for r in results]) or 0.0
    for key in RAGAS_METRICS:
        summary[key] = _mean([r.get("metrics", {}).get(key) for r in results])
    return summary


def _fmt_metric(value: Any) -> str:
    num = _safe_float(value)
    return "N/A" if num is None else f"{num:.4f}"


def _truncate(text: str, limit: int = 800) -> str:
    return text if len(text or "") <= limit else text[:limit].rstrip() + "..."


def _render_md(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# RAGAS 评估报告 (rag_lab)",
        "",
        "## 1. 运行参数",
        f"- run_name: `{report.get('run_name')}`",
        f"- total_questions: {report.get('total_questions')}",
        f"- top_k: {report.get('top_k')}",
        f"- retrieval_mode: {report.get('retrieval_mode')}",
        f"- chunk_strategy: {report.get('chunk_strategy')}",
        f"- use_rerank: {str(report.get('use_rerank')).lower()}",
        f"- skip_ragas: {str(report.get('skip_ragas')).lower()}",
        f"- generated_at: {report.get('generated_at')}",
        "",
        "## 2. 总体指标",
        f"- Hit@K: {_fmt_metric(summary.get('hit_at_k'))}",
        f"- Recall@K: {_fmt_metric(summary.get('recall_at_k'))}",
        f"- MRR: {_fmt_metric(summary.get('mrr'))}",
        f"- Keyword Hit: {_fmt_metric(summary.get('keyword_hit'))}",
        f"- Faithfulness: {_fmt_metric(summary.get('faithfulness'))}",
        f"- Answer Relevancy: {_fmt_metric(summary.get('answer_relevancy'))}",
        f"- Context Precision: {_fmt_metric(summary.get('context_precision'))}",
        f"- Context Recall: {_fmt_metric(summary.get('context_recall'))}",
        "",
        "## 3. 每个问题结果",
        "",
    ]
    failed = []
    for result in report.get("results", []):
        if result.get("error"):
            failed.append(result.get("id"))
        source_names = [_source_name(src) for src in result.get("sources", [])]
        source_text = ", ".join(f"`{name}`" for name in source_names if name) or "无"
        lines.extend([
            f"### {result.get('id')} - {result.get('question')}",
            "",
            f"- question: {result.get('question')}",
            f"- ground_truth: {_truncate(result.get('ground_truth') or '', 500)}",
            f"- answer: {_truncate(result.get('answer') or '', 800)}",
            f"- contexts: {len(result.get('contexts') or [])}",
            f"- sources: {source_text}",
            f"- expected_source: {result.get('expected_source') or '无'}",
            f"- expected_source_hit: {result.get('expected_source_hit')}",
            f"- keyword_hit: {result.get('keyword_hit')}",
            f"- rank: {result.get('rank')}",
            f"- error: {result.get('error')}",
            "",
        ])
    lines.extend(["## 4. 失败问题列表", ""])
    if failed:
        lines.extend([f"- {item}" for item in failed])
    else:
        lines.append("- 无")
    lines.extend([
        "",
        "## 5. 迁移建议",
        "",
        "- 对比 chunk_strategy=paragraph/recursive/sentence_window/markdown_header 的命中率与 Keyword Hit，优先保留指标稳定的策略。",
        "- 如果 hybrid 下 sources 缺失，先调高 dense_weight 或回退到 vector 进行对照。",
        "- rerank 仅在高召回场景下开启，观察 MRR 与 Answer Relevancy 是否提升。",
        "",
    ])
    return "\n".join(lines)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    questions = _normalize_questions(_read_json(args.questions), args.limit)
    run_name = f"ragas_eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    build_result = await pipeline.build_index(chunk_strategy=args.chunk_strategy)

    results: list[dict[str, Any]] = []
    for question in questions:
        try:
            if not question.get("question"):
                raise ValueError("question is empty")
            rag_output = await pipeline.ask_question(
                question["question"],
                top_k=args.top_k,
                retrieval_mode=args.retrieval_mode,
                use_reranker=args.use_rerank,
            )
            results.append(_build_result(question, rag_output, args.top_k))
        except Exception as exc:
            results.append(_build_error_result(question, exc))

    ragas_error = None
    if not args.skip_ragas:
        ragas_error = await _run_ragas(results)

    summary = _build_summary(results)
    report = {
        "run_name": run_name,
        "generated_at": _utc_now(),
        "total_questions": len(results),
        "top_k": args.top_k,
        "retrieval_mode": args.retrieval_mode,
        "chunk_strategy": args.chunk_strategy,
        "use_rerank": args.use_rerank,
        "skip_ragas": args.skip_ragas,
        "ragas_error": ragas_error,
        "build_index": build_result,
        "summary": summary,
        "results": results,
    }
    _write_json(args.output_json, report)
    _write_text(args.output_md, _render_md(report))
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ragas evaluation for rag_lab.")
    parser.add_argument("--questions", default="backend/rag_lab/eval/eval_questions.json", help="Path to eval_questions.json")
    parser.add_argument("--output-json", default="backend/rag_lab/eval/ragas_report.json", help="Path to output JSON report")
    parser.add_argument("--output-md", default="backend/rag_lab/eval/ragas_report.md", help="Path to output Markdown report")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K used for retrieval metrics")
    parser.add_argument("--retrieval-mode", default="hybrid", help="vector|keyword|hybrid")
    parser.add_argument("--chunk-strategy", default="paragraph", help="paragraph|recursive|sentence_window|markdown_header")
    parser.add_argument("--use-rerank", action="store_true", help="Enable rerank in evaluation")
    parser.add_argument("--skip-ragas", action="store_true", help="Skip ragas metrics even if installed")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report = asyncio.run(_run(args))
    print(
        "Ragas evaluation finished: "
        f"questions={report['total_questions']} "
        f"hit_at_k={_fmt_metric(report['summary'].get('hit_at_k'))} "
        f"json={args.output_json} md={args.output_md}"
    )
    if report.get("ragas_error"):
        print("Ragas fallback: basic metrics were written; see ragas_error in the report.")


if __name__ == "__main__":
    main()
