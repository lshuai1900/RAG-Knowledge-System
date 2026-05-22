from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

THIS_FILE = Path(__file__).resolve()
YUXI_RAG_DIR = THIS_FILE.parent
RAG_LAB_DIR = YUXI_RAG_DIR.parent
BACKEND_DIR = RAG_LAB_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
for candidate in (YUXI_RAG_DIR, RAG_LAB_DIR, BACKEND_DIR, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from .chunker import DEFAULT_CHUNKS_PATH, chunk_paragraphs, save_chunks
    from .embeddings import EmbeddingClient
    from .generator import AnswerGenerator
    from .loader import DEFAULT_DOCS_DIR, load_documents
    from .parser import parse_documents
    from .reranker import rerank_if_available
    from .retriever import Retriever
    from .vector_store import DEFAULT_INDEX_DIR, LocalVectorStore
except ImportError:  # pragma: no cover - direct script execution
    from chunker import DEFAULT_CHUNKS_PATH, chunk_paragraphs, save_chunks
    from embeddings import EmbeddingClient
    from generator import AnswerGenerator
    from loader import DEFAULT_DOCS_DIR, load_documents
    from parser import parse_documents
    from reranker import rerank_if_available
    from retriever import Retriever
    from vector_store import DEFAULT_INDEX_DIR, LocalVectorStore


async def build_index(
    docs_dir: str | Path = DEFAULT_DOCS_DIR,
    index_dir: str | Path = DEFAULT_INDEX_DIR,
    chunks_path: str | Path = DEFAULT_CHUNKS_PATH,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> dict[str, Any]:
    docs = load_documents(docs_dir)
    if not docs:
        raise RuntimeError(f"No supported documents found in {Path(docs_dir).resolve()}")

    paragraphs = parse_documents(docs)
    chunks = chunk_paragraphs(paragraphs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        raise RuntimeError("Documents were loaded but no chunks were produced")

    save_chunks(chunks, chunks_path)
    embeddings = await EmbeddingClient().embed_documents([chunk.chunk_text for chunk in chunks])
    store = LocalVectorStore(index_dir)
    store.save(embeddings, chunks)

    return {
        "docs_dir": str(Path(docs_dir).resolve()),
        "index_dir": str(Path(index_dir).resolve()),
        "chunks_path": str(Path(chunks_path).resolve()),
        "documents": len(docs),
        "paragraphs": len(paragraphs),
        "chunks": len(chunks),
        "embedding_dim": len(embeddings[0]) if embeddings else 0,
    }


async def ask_question(
    question: str,
    top_k: int = 5,
    index_dir: str | Path = DEFAULT_INDEX_DIR,
    use_mmr: bool = False,
    lambda_mult: float = 0.5,
    use_reranker: bool = False,
    retrieval_only: bool = False,
) -> dict[str, Any]:
    retriever = Retriever(index_dir=index_dir)
    results = await retriever.retrieve(
        question,
        top_k=top_k,
        use_mmr=use_mmr,
        lambda_mult=lambda_mult,
    )
    results = await rerank_if_available(question, results, use_reranker=use_reranker)
    results = results[:top_k]

    if retrieval_only:
        contexts = [item.get("chunk_text", "") for item in results]
        sources = [
            {
                "source": (item.get("metadata") or {}).get("source", ""),
                "chunk_id": item.get("chunk_id"),
                "chunk_index": (item.get("metadata") or {}).get("chunk_index"),
                "score": item.get("score"),
                "content": item.get("chunk_text", "")[:500],
                "metadata": item.get("metadata") or {},
            }
            for item in results
        ]
        return {"answer": "", "contexts": contexts, "sources": sources, "raw_results": results}

    answer = await AnswerGenerator().generate(question, results)
    answer["raw_results"] = results
    return answer


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone Yuxi-RAG experiment pipeline.")
    parser.add_argument("--build-index", action="store_true", help="Build local numpy vector index from backend/rag_lab/data/docs")
    parser.add_argument("--ask", default=None, help="Ask a question against the local experiment index")
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR), help="Directory containing experiment documents")
    parser.add_argument("--index-dir", default=str(DEFAULT_INDEX_DIR), help="Directory for embeddings.npy and metadata.json")
    parser.add_argument("--chunks-path", default=str(DEFAULT_CHUNKS_PATH), help="Path for generated chunks.json")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Target chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap in characters")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--use-mmr", action="store_true", help="Use MMR instead of plain cosine Top-K")
    parser.add_argument("--lambda-mult", type=float, default=0.5, help="MMR relevance/diversity balance")
    parser.add_argument("--use-reranker", action="store_true", help="Try current project reranker if enabled; otherwise no-op")
    parser.add_argument("--retrieval-only", action="store_true", help="Only retrieve contexts, do not call the chat model")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.build_index:
        return {"build_index": await build_index(
            docs_dir=args.docs_dir,
            index_dir=args.index_dir,
            chunks_path=args.chunks_path,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )}

    if args.ask:
        return {"question": args.ask, **await ask_question(
            args.ask,
            top_k=args.top_k,
            index_dir=args.index_dir,
            use_mmr=args.use_mmr,
            lambda_mult=args.lambda_mult,
            use_reranker=args.use_reranker,
            retrieval_only=args.retrieval_only,
        )}

    raise RuntimeError("Nothing to do. Use --build-index or --ask.")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
