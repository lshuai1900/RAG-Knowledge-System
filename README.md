# RAG Knowledge System

面向中文文档的本地 RAG 知识库系统，支持零 API Key 演示模式。

> **架构参考**: RAG 核心模块设计参考 [Yuxi](https://github.com/xerrors/Yuxi) 项目（MIT License）的 KnowledgeBase / Manager / Factory / ParserRegistry / ChunkingDispatcher 架构。

## 核心能力

- **零 API Key 演示模式** — `EMBEDDING_PROVIDER=hash`，上传→分块→索引→检索→sources 全流程可跑通
- **文档解析** — 支持 PDF / TXT / MD / DOCX / DOC，ParserRegistry 按文件类型自动分发
- **多策略分块** — auto / recursive / markdown_header（章节）/ sentence_window（中文标点）/ paragraph
- **双 Embedding Provider** — hash（SHA-256 零网络）/ openai_compatible（生产语义检索）
- **混合检索** — Dense 向量 + Sparse BM25/jieba，RRF/weighted_score 融合，可选 Rerank
- **引用溯源** — sources 含 dense/sparse/fusion/rerank 分数、分块策略、章节信息
- **RAG 状态可观测** — embedding provider / chunk 数 / index_ready / health
- **专业前端控制台** — React + Vite + TypeScript + Tailwind CSS，五视图管理

## 主调用链

```
API endpoint
  → rag.service
    → KnowledgeBaseManager
      → ParserRegistry (TextParser / PdfParser / DocxParser)
      → ChunkingDispatcher (auto → markdown_header / sentence_window / recursive)
      → EmbeddingProvider (hash / openai_compatible)
      → ChunkStore / VectorStore (JSON + numpy)
      → RetrievalPipeline (dense cosine → sources)
      → StatusRuntime (RAG status)
```

## 项目结构

```
backend/
  app/                        # FastAPI 应用 + API endpoints
  rag/                        # Yuxi-style RAG 主流程 ★
    core/                     # manager, factory, schemas, exceptions
    parsers/                  # ParserRegistry
    chunking/                 # dispatcher + 4 strategies
    embeddings/               # hash / openai_compatible
    retrieval/                # RetrievalPipeline
    storage/                  # DocumentStore / ChunkStore / VectorStore
    evaluation/               # runner（最小闭环）
    service.py                # RagService — 统一入口
  rag_lab/                    # Legacy / eval / deprecated
frontend/
  src/components/
    Layout/    Dashboard, Sidebar, ChatView, DocumentView, ...
    Chat/      ChatInput, MessageList, SourceCitation
    Document/  Uploader, List, RagEngineStatusPanel
    KnowledgeBase/
    shared/    Card, Badge, EmptyState, StatusPill
```

## 快速开始

### 前置：Python 3.10+, Node.js 18+

```bash
git clone https://github.com/lshuai1900/RAG-Knowledge-System.git
cd RAG-Knowledge-System
```

### 后端

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env          # 默认 hash 演示模式，无需 API Key
PYTHONPATH=backend python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger: `http://localhost:8000/docs`
- RAG Status: `http://localhost:8000/api/v1/rag/status`

### 前端

```bash
npm --prefix frontend install
npm --prefix frontend run dev -- --host 0.0.0.0
```

访问 `http://localhost:5173`

## 演示模式 vs 生产模式

| 配置 | 演示 | 生产 |
|------|------|------|
| `EMBEDDING_PROVIDER` | `hash` | `openai` |
| API Key | 不需要 | 需要 |
| 语义检索 | SHA-256 伪向量 | 真实语义相似度 |
| 切换后 | — | 需重建索引 |

### 远程 Embedding 常见错误

- `EMBEDDING_API_BASE` 指向 Chat endpoint（如 deepseek），该 endpoint 不支持 embeddings
- Chat Model 名用作 Embedding Model（`deepseek-chat` 不支持 embeddings）
- `EMBEDDING_API_KEY` 未设置或过期

## Chunk Strategy

| 策略 | 文档 | 说明 |
|------|------|------|
| `auto` | 全部 | .md→markdown_header, .txt→sentence_window, 其他→recursive |
| `recursive` | PDF/DOCX | 通用递归分块 |
| `markdown_header` | MD | 按 # 标题层级分块，含 section_title |
| `sentence_window` | TXT | 中文标点滑动窗口 |
| `paragraph` | 通用 | 按双换行分段 |

## Sources 字段

`dense_score` / `sparse_score` / `fusion_score` / `rerank_score` — 未启用为 `null`。`chunk_strategy` / `section_title` 来自分块 metadata。

## RAG Status 字段

`embedding_provider` / `embedding_dim` / `chunks_count` / `index_ready` / `health` / `last_index_time`

## Evaluation

最小闭环：`rag/evaluation/runner.py` 生成基础 eval report。完整 Ragas 需安装 ragas + 配置 LLM_API_KEY，运行 `backend/rag_lab/eval/run_ragas_eval.py`。

## 前端

五视图：总览 / 知识库 / 文档管理 / 智能问答 / RAG 引擎。支持流式问答、Markdown 渲染、引用溯源、状态监控。

## License

MIT — RAG 核心架构参考 [Yuxi](https://github.com/xerrors/Yuxi) (MIT License)
