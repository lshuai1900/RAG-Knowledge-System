# RAG Knowledge System

RAG Knowledge System is an open-source knowledge-base question answering system built around Retrieval-Augmented Generation (RAG). It supports document upload and parsing, multiple chunking strategies, OpenAI-compatible embeddings, local vector indexing, Hybrid Search, optional reranking, LLM answers with citations, Ragas/basic evaluation scripts, frontend RAG status visualization, and a legacy fallback path.

## Features

- Knowledge base and document management from a React frontend.
- Document upload, parsing, chunking, indexing, and rebuild operations.
- Chunk strategies: `semantic`, `paragraph`, `recursive`, `sentence_window`, `markdown_header`.
- Retrieval modes: `vector`, `keyword`, `hybrid`.
- Fusion strategies: `rrf`, `weighted_score`.
- Optional rerank stage with configurable Top N.
- Local numpy vector index for the enhanced `rag_lab` engine.
- Legacy fallback flow for the original backend RAG path.
- Evaluation scripts for Hit@K, Recall@K, MRR, keyword hit, and optional Ragas metrics.
- Frontend RAG status panel for current engine/config visibility.
- Source citation cards with score, dense score, sparse score, fusion score, rerank score, and chunk strategy.

## Tech Stack

- Backend: FastAPI / Python
- Frontend: React / Vite / TypeScript
- Vector index: local numpy index
- RAG evaluation: optional Ragas
- LLM / Embedding: OpenAI-compatible API
- Optional legacy vector store: Milvus Lite / Milvus-compatible path

## Project Structure

```text
.
├── backend/
│   ├── app/                         # FastAPI app, APIs, services, models, DB adapters
│   ├── rag_lab/                     # Enhanced RAG lab engine and evaluation tools
│   │   ├── yuxi_rag/                # Loader, chunker, retriever, hybrid search, reranker, generator
│   │   ├── eval/                    # Smoke, parameter experiments, Ragas/basic eval scripts
│   │   └── data/                    # Runtime docs/chunks/index; generated files are ignored
│   └── requirements.txt             # Main backend dependencies
├── frontend/
│   └── src/                         # React app, components, API clients, hooks, store, types
├── docker-compose.yml               # Optional local orchestration
├── .env.example                     # Safe placeholder environment file
└── README.md
```

## Quick Start

### 1. Clone

```bash
git clone <your-repo-url>
cd RAG-Knowledge-System
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Install optional rag_lab evaluation dependencies

Install these when you want to run `backend/rag_lab` experiments or optional Ragas evaluation:

```bash
pip install -r backend/rag_lab/requirements-rag-lab.txt
```

### 5. Install frontend dependencies

```bash
npm --prefix frontend install
```

### 6. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your own OpenAI-compatible chat and embedding credentials. Do not commit `.env`.

### 7. Start the backend

```bash
PYTHONPATH=backend RAG_ENGINE=rag_lab DEBUG=false \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend API:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- RAG status: `http://localhost:8000/api/v1/rag/status`

### 8. Start the frontend

```bash
npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
```

Frontend UI:

- `http://localhost:5173`

## Environment Variables

Common defaults for the enhanced RAG flow:

```env
RAG_ENGINE=rag_lab
CHUNK_STRATEGY=semantic
RAG_RETRIEVAL_MODE=hybrid
RAG_HYBRID_FUSION=rrf
RAG_USE_RERANK=false
RAG_RERANK_TOP_N=5

LLM_API_KEY=
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-chat-model
CHAT_MODEL=your-chat-model

EMBED_MODEL=your-embedding-model
EMBEDDING_MODEL_NAME=your-embedding-model
EMBEDDING_API_KEY=
EMBEDDING_API_BASE=https://api.example.com/v1
```

Additional backend variables such as `DATABASE_URL`, `UPLOAD_DIR`, `SIMILARITY_SCORE_THRESHOLD`, `TOP_K`, and legacy Milvus/BM25 settings are documented in `.env.example`.

## RAG Modes

### `RAG_ENGINE=rag_lab`

The enhanced RAG engine. It uses the `backend/rag_lab/yuxi_rag/` modules for document loading, chunking, local vector indexing, vector/keyword/hybrid retrieval, optional rerank, and answer generation.

Useful knobs:

- `CHUNK_STRATEGY`: `semantic`, `paragraph`, `recursive`, `sentence_window`, `markdown_header`
- `RAG_RETRIEVAL_MODE`: `vector`, `keyword`, `hybrid`
- `RAG_HYBRID_FUSION`: `rrf`, `weighted_score`
- `RAG_USE_RERANK`: `true` or `false`
- `RAG_RERANK_TOP_N`: number of chunks kept after rerank

### `RAG_ENGINE=legacy`

The original backend RAG flow. Keep this path available as a rollback mechanism for deployments that still depend on the previous Milvus/BM25 service flow.

## Evaluation Scripts

Run from the repository root after installing dependencies and configuring `.env`:

```bash
python backend/rag_lab/eval/smoke_test_main_rag.py
python backend/rag_lab/eval/run_param_experiments.py
python backend/rag_lab/eval/run_ragas_eval.py --skip-ragas
```

The evaluation scripts support basic retrieval metrics such as Hit@K, Recall@K, MRR, and keyword hit. Ragas metrics are optional and live in `backend/rag_lab/requirements-rag-lab.txt` so they do not have to be installed for the main backend path.

Generated reports are ignored by git:

- `backend/rag_lab/eval/*report*.json`
- `backend/rag_lab/eval/*report*.md`

## Frontend RAG Visualization

The frontend includes a RAG engine status panel in the document/knowledge-base area. It shows:

- Current engine: `rag_lab` or `legacy`
- Chunk strategy
- Retrieval mode
- Fusion method
- Rerank enabled/disabled
- Rerank Top N
- A visual pipeline: document upload → chunking → embedding → hybrid search → rerank → LLM answer

Answer sources are shown as cards with:

- Source filename
- Chunk strategy tag
- Total score
- Context summary
- Collapsible advanced scores: `dense_score`, `sparse_score`, `fusion_score`, `rerank_score`

## Open Source Hygiene

Do not commit local runtime or sensitive files:

- `.env` or any file containing API keys
- `.venv/`, `venv/`
- `node_modules/`
- frontend `dist/` or `build/`
- uploaded documents
- generated vector indexes and chunk files
- generated evaluation reports
- local caches such as `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`

The repository keeps only source code, example configuration, sample documents, and reproducible scripts.

## License

License: MIT recommended. Please add LICENSE before publishing.
