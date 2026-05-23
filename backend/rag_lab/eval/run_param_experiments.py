from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
RAG_LAB_DIR = THIS_FILE.parents[1]
BACKEND_DIR = RAG_LAB_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
for candidate in (RAG_LAB_DIR, BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from yuxi_rag.pipeline import build_index  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chunking parameter experiments for Yuxi-RAG.")
    parser.add_argument(
        "--strategies",
        default="paragraph,recursive,sentence_window,markdown_header",
        help="Comma-separated chunk strategies",
    )
    parser.add_argument("--chunk-size", type=int, default=800, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=120, help="Chunk overlap in characters")
    parser.add_argument("--docs-dir", default=str(RAG_LAB_DIR / "data" / "docs"), help="Docs directory")
    parser.add_argument("--index-dir", default=str(RAG_LAB_DIR / "data" / "index"), help="Index directory")
    parser.add_argument("--chunks-path", default=str(RAG_LAB_DIR / "data" / "chunks" / "chunks.json"), help="Chunks output path")
    parser.add_argument("--output-json", default=None, help="Optional output JSON path")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> list[dict]:
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    results: list[dict] = []
    for strategy in strategies:
        result = await build_index(
            docs_dir=args.docs_dir,
            index_dir=args.index_dir,
            chunks_path=args.chunks_path,
            chunk_strategy=strategy,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    results = asyncio.run(_run(args))
    payload = {"experiments": results}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output_json:
        output = Path(args.output_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
