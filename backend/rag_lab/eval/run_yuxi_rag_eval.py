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

from yuxi_rag.pipeline import ask_question  # noqa: E402

SUMMARY_KEYS = [
    "hit_at_k",
    "recall_at_k",
    "mrr",
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
]
RAGAS_METRIC_KEYS = [
    "faithfulness",
    "answer_relevancy",
    "response_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
]


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
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


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
        q.setdefault("expected_sources", [])
        q.setdefault("expected_keywords", [])
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


def _find_expected_rank(sources: list[dict[str, Any]], expected_sources: list[str]) -> int | None:
    if not expected_sources:
        return None
    for idx, src in enumerate(sources, start=1):
        name = _source_name(src)
        if any(_source_matches_expected(name, expected) for expected in expected_sources):
            return idx
    return None


def _recall_at_k(sources: list[dict[str, Any]], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0
    if not sources:
        return 0.0
    hits = 0
    for expected in expected_sources:
        if any(_source_matches_expected(_source_name(src), expected) for src in sources):
            hits += 1
    return hits / len(expected_sources)


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
    expected_sources = question.get("expected_sources") or []
    expected_keywords = question.get("expected_keywords") or []
    rank = _find_expected_rank(sources[:top_k], expected_sources)
    expected_source_hit = rank is not None if expected_sources else True
    recall = _recall_at_k(sources[:top_k], expected_sources)
    return {
        "id": question.get("id"),
        "question": question.get("question"),
        "ground_truth": question.get("ground_truth", ""),
        "answer": rag_output.get("answer", ""),
        "sources": sources,
        "contexts": contexts,
        "expected_sources": expected_sources,
        "expected_keywords": expected_keywords,
        "expected_source_hit": expected_source_hit,
        "keyword_hit": _keyword_hit(rag_output.get("answer", ""), contexts, expected_keywords),
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
        "expected_sources": question.get("expected_sources") or [],
        "expected_keywords": question.get("expected_keywords") or [],
        "expected_source_hit": False,
        "keyword_hit": False,
        "rank": None,
        "metrics": {"hit_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0},
        "error": f"{type(error).__name__}: {error}",
    }


def _load_ragas_metrics(include_answer_correctness: bool) -> tuple[list[Any], list[str]]:
    from ragas import metrics as ragas_metrics  # type: ignore

    requested = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    if include_answer_correctness:
        requested.append("answer_correctness")

    loaded: list[Any] = []
    names: list[str] = []
    for name in requested:
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
        include_correctness = any((r.get("ground_truth") or "").strip() for r in rows_for_ragas)
        metrics, metric_names = _load_ragas_metrics(include_correctness)
        if not metrics:
            return "No compatible Ragas metrics found in installed ragas version"
        dataset = _make_ragas_dataset(rows_for_ragas)
        score = await asyncio.to_thread(lambda: evaluate(dataset, metrics=metrics))
        ragas_rows = _ragas_scores_to_rows(score)
        for result, ragas_row in zip(rows_for_ragas, ragas_rows):
            metrics_dict = result.setdefault("metrics", {})
            for key in RAGAS_METRIC_KEYS + metric_names:
                if key in ragas_row:
                    normalized_key = "answer_relevancy" if key == "response_relevancy" else key
                    value = _safe_float(ragas_row.get(key))
                    if value is not None:
                        metrics_dict[normalized_key] = value
        return None
    except Exception as exc:
        return f"Ragas evaluation failed: {type(exc).__name__}: {exc}"


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {key: None for key in SUMMARY_KEYS}
    summary["hit_at_k"] = _mean([r.get("metrics", {}).get("hit_at_k") for r in results]) or 0.0
    summary["recall_at_k"] = _mean([r.get("metrics", {}).get("recall_at_k") for r in results]) or 0.0
    summary["mrr"] = _mean([r.get("metrics", {}).get("mrr") for r in results]) or 0.0
    for key in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]:
        summary[key] = _mean([r.get("metrics", {}).get(key) for r in results])
    return summary


def _fmt_metric(value: Any) -> str:
    num = _safe_float(value)
    return "N/A" if num is None else f"{num:.4f}"


def _truncate(text: str, limit: int = 800) -> str:
    return text if len(text or "") <= limit else text[:limit].rstrip() + "..."


def _build_diagnostics(summary: dict[str, Any], args: argparse.Namespace, ragas_error: str | None) -> list[str]:
    diagnostics: list[str] = []
    if ragas_error:
        diagnostics.append(f"Ragas 未完成：{ragas_error}。基础检索指标仍然有效。")
    if (summary.get("hit_at_k") or 0.0) < 0.6:
        diagnostics.append("Hit@K 低：建议调整 chunk_size、chunk_overlap、top_k 或启用 MMR/Reranker 实验。")
    if args.retrieval_only:
        diagnostics.append("当前为 retrieval-only 模式：不会生成答案，也不会运行 Ragas 生成类指标。")
    elif args.skip_ragas:
        diagnostics.append("当前设置了 --skip-ragas：只输出基础检索指标和问答结果。")
    if not diagnostics:
        diagnostics.append("未发现明显异常，可继续对比分块参数、MMR 和 Reranker 实验结果。")
    return diagnostics


def _render_md(report: dict[str, Any], args: argparse.Namespace) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Yuxi-RAG 实验评估报告",
        "",
        "## 1. 运行信息",
        f"- run_name: `{report.get('run_name')}`",
        f"- total_questions: {report.get('total_questions')}",
        f"- top_k: {report.get('top_k')}",
        f"- retrieval_only: {str(report.get('retrieval_only')).lower()}",
        f"- skip_ragas: {str(report.get('skip_ragas')).lower()}",
        f"- generated_at: {report.get('generated_at')}",
        "",
        "## 2. 总体指标",
        f"- Hit@K: {_fmt_metric(summary.get('hit_at_k'))}",
        f"- Recall@K: {_fmt_metric(summary.get('recall_at_k'))}",
        f"- MRR: {_fmt_metric(summary.get('mrr'))}",
        f"- Faithfulness: {_fmt_metric(summary.get('faithfulness'))}",
        f"- Answer Relevancy: {_fmt_metric(summary.get('answer_relevancy'))}",
        f"- Context Precision: {_fmt_metric(summary.get('context_precision'))}",
        f"- Context Recall: {_fmt_metric(summary.get('context_recall'))}",
        f"- Answer Correctness: {_fmt_metric(summary.get('answer_correctness'))}",
        "",
        "## 3. 每个问题结果",
        "",
    ]
    for result in report.get("results", []):
        metrics = result.get("metrics", {})
        source_names = [_source_name(src) for src in result.get("sources", [])]
        source_text = ", ".join(f"`{name}`" for name in source_names if name) or "无"
        lines.extend([
            f"### {result.get('id')} - {result.get('question')}",
            "",
            f"- question: {result.get('question')}",
            f"- ground_truth: {_truncate(result.get('ground_truth') or '', 500)}",
            f"- answer: {_truncate(result.get('answer') or '', 800)}",
            f"- sources: {source_text}",
            f"- expected_source_hit: {result.get('expected_source_hit')}",
            f"- keyword_hit: {result.get('keyword_hit')}",
            f"- rank: {result.get('rank')}",
            f"- metrics:",
            f"  - hit_at_k: {_fmt_metric(metrics.get('hit_at_k'))}",
            f"  - recall_at_k: {_fmt_metric(metrics.get('recall_at_k'))}",
            f"  - mrr: {_fmt_metric(metrics.get('mrr'))}",
            f"  - faithfulness: {_fmt_metric(metrics.get('faithfulness'))}",
            f"  - answer_relevancy: {_fmt_metric(metrics.get('answer_relevancy'))}",
            f"  - context_precision: {_fmt_metric(metrics.get('context_precision'))}",
            f"  - context_recall: {_fmt_metric(metrics.get('context_recall'))}",
            f"  - answer_correctness: {_fmt_metric(metrics.get('answer_correctness'))}",
            f"- error: {result.get('error')}",
            "",
        ])
    lines.extend(["## 4. 自动诊断", ""])
    for item in report.get("diagnostics", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    questions = _normalize_questions(_read_json(args.questions), args.limit)
    run_name = args.run_name or f"yuxi_rag_eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    results: list[dict[str, Any]] = []
    for question in questions:
        try:
            if not question.get("question"):
                raise ValueError("question is empty")
            rag_output = await ask_question(
                question["question"],
                top_k=args.top_k,
                use_mmr=args.use_mmr,
                lambda_mult=args.lambda_mult,
                use_reranker=args.use_reranker,
                retrieval_only=args.retrieval_only,
            )
            results.append(_build_result(question, rag_output, args.top_k))
        except Exception as exc:
            results.append(_build_error_result(question, exc))

    ragas_error = None
    if not args.retrieval_only and not args.skip_ragas:
        ragas_error = await _run_ragas(results)

    summary = _build_summary(results)
    report = {
        "run_name": run_name,
        "generated_at": _utc_now(),
        "total_questions": len(results),
        "top_k": args.top_k,
        "retrieval_only": args.retrieval_only,
        "skip_ragas": args.skip_ragas,
        "use_mmr": args.use_mmr,
        "lambda_mult": args.lambda_mult,
        "use_reranker": args.use_reranker,
        "ragas_error": ragas_error,
        "summary": summary,
        "results": results,
        "diagnostics": _build_diagnostics(summary, args, ragas_error),
    }
    _write_json(args.output_json, report)
    _write_text(args.output_md, _render_md(report, args))
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline evaluation for the Yuxi-RAG experiment module.")
    parser.add_argument("--questions", default="backend/rag_lab/eval/eval_questions.json", help="Path to eval_questions.json")
    parser.add_argument("--output-json", default="backend/rag_lab/eval/eval_report.json", help="Path to output JSON report")
    parser.add_argument("--output-md", default="backend/rag_lab/eval/eval_report.md", help="Path to output Markdown report")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K used for retrieval metrics")
    parser.add_argument("--retrieval-only", action="store_true", help="Only run retrieval metrics, do not call LLM or Ragas")
    parser.add_argument("--skip-ragas", action="store_true", help="Run RAG but skip Ragas metrics")
    parser.add_argument("--run-name", default=None, help="Custom run name for the report")
    parser.add_argument("--use-mmr", action="store_true", help="Use MMR retrieval in the experiment pipeline")
    parser.add_argument("--lambda-mult", type=float, default=0.5, help="MMR relevance/diversity balance")
    parser.add_argument("--use-reranker", action="store_true", help="Try current project reranker if enabled; otherwise no-op")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report = asyncio.run(_run(args))
    print(
        "Yuxi-RAG evaluation finished: "
        f"questions={report['total_questions']} "
        f"hit_at_k={_fmt_metric(report['summary'].get('hit_at_k'))} "
        f"json={args.output_json} md={args.output_md}"
    )
    if report.get("ragas_error"):
        print("Ragas fallback: basic metrics were written; see ragas_error in the report.")


if __name__ == "__main__":
    main()
