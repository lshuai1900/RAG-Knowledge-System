# RAG Knowledge System

面向中文论文/文档问答的本地 RAG 知识库系统。支持文档上传、多策略分块、向量/关键词/混合检索、可选 Rerank、LLM 问答与引用溯源，提供专业级 AI 控制台前端。

## 功能特性

**知识库与文档管理**
- 知识库 CRUD，每个知识库独立配置索引与检索策略
- 文档上传支持 PDF / TXT / MD / DOCX，自动解析与分块
- 索引状态实时监控，文档就绪状态轮询
- 一键索引重建，结果摘要展示

**检索增强生成**
- 多策略分块：`semantic` / `paragraph` / `recursive` / `sentence_window` / `markdown_header`
- 三种检索模式：`vector` / `keyword` / `hybrid`
- 混合检索融合：`rrf` / `weighted_score`
- 可选 Rerank，支持配置 Top N
- 流式 LLM 回答 + 引用溯源（含 dense/sparse/fusion/rerank 分数）

**双引擎架构**
- `rag_lab` — 增强 RAG 引擎，本地 numpy 向量索引、混合检索、可选重排
- `legacy` — 原始 Milvus / BM25 路径，保留作为回滚机制

**自动评估**
- 基础检索指标：Hit@K、Recall@K、MRR、keyword_hit
- 可选 Ragas 端到端评估

**专业前端控制台**
- 总览仪表盘、知识库管理、文档管理、智能问答、RAG 引擎状态五视图
- 引用溯源卡片（分数折叠、分块策略标签、内容摘要）
- RAG 流水线可视化（文档上传 → 分块 → Embedding → Hybrid Search → Rerank → LLM 回答）
- 浅色 AI SaaS 控制台风格，响应式适配桌面/平板/手机

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI (Python) |
| 向量索引 | local numpy index (rag_lab) / Milvus Lite (legacy) |
| 文本检索 | BM25 (legacy 混合检索) |
| LLM / Embedding | OpenAI-compatible API |
| 前端框架 | React 19 + Vite 8 + TypeScript |
| 样式方案 | Tailwind CSS 4 |
| 状态管理 | Zustand |
| 前端依赖 | lucide-react、react-markdown、rehype-highlight、remark-gfm、axios |
| RAG 评估 | Ragas (可选) |

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 应用入口
│   │   ├── config.py                  # 配置管理（读取环境变量）
│   │   ├── api/
│   │   │   ├── router.py              # API 路由注册
│   │   │   └── endpoints/             # chat / document / knowledge_base / rag / health
│   │   ├── core/                      # 异常处理、依赖注入
│   │   ├── db/                        # Milvus 客户端、SQLite 数据库适配
│   │   ├── models/                    # ORM / Pydantic 模型
│   │   └── services/                  # 业务逻辑层（embedding / ingestion / llm / bm25 / hybrid search）
│   ├── rag_lab/
│   │   ├── yuxi_rag/                  # loader / chunker / retriever / hybrid search / reranker / generator
│   │   ├── eval/                      # smoke 测试、参数实验、Ragas 评估脚本
│   │   └── data/                      # 运行时 chunks / index（gitignore）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Layout/                # AppLayout、Sidebar、DashboardView、ChatView 等页面组件
│       │   ├── Chat/                  # ChatInput、MessageList、MessageBubble、SourceCitation
│       │   ├── Document/              # DocumentUploader、DocumentList、IndexStatusPanel、RagEngineStatusPanel
│       │   ├── KnowledgeBase/         # KnowledgeBaseList、KnowledgeBaseForm
│       │   └── shared/               # Card、Badge、EmptyState、LoadingState、StatusPill 等通用组件
│       ├── api/                       # axios 客户端与 API 封装
│       ├── hooks/                     # useStreamChat（SSE 流式问答）
│       ├── store/                     # Zustand 全局状态
│       └── types/                     # TypeScript 类型定义
├── docker-compose.yml
├── .env.example
└── README.md
```

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- OpenAI-compatible Chat / Embedding API（如阿里云 DashScope、DeepSeek、OpenAI 等）

### 1. 克隆仓库

```bash
git clone https://github.com/lshuai1900/RAG-Knowledge-System.git
cd RAG-Knowledge-System
```

### 2. 安装后端依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

如需运行评估脚本，额外安装：

```bash
pip install -r backend/rag_lab/requirements-rag-lab.txt
```

### 3. 安装前端依赖

```bash
npm --prefix frontend install
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填入以下配置：

```env
# 核心引擎
RAG_ENGINE=rag_lab
CHUNK_STRATEGY=semantic
RAG_RETRIEVAL_MODE=hybrid
RAG_HYBRID_FUSION=rrf

# Chat 模型
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-chat-model

# Embedding 模型
EMBEDDING_API_KEY=your_embedding_api_key_here
EMBEDDING_API_BASE=https://api.example.com/v1
EMBED_MODEL=your-embedding-model
```

完整配置项见 [.env.example](.env.example)。

### 5. 启动后端

```bash
PYTHONPATH=backend RAG_ENGINE=rag_lab python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API 根地址：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- RAG 状态接口：`http://localhost:8000/api/v1/rag/status`

### 6. 启动前端

```bash
npm --prefix frontend run dev
```

访问 `http://localhost:5173` 进入 RAG Knowledge Console。

### 7. Docker 启动（可选）

```bash
docker compose up -d
```

## 环境变量说明

### RAG 引擎

| 变量 | 说明 | 可选值 |
|------|------|--------|
| `RAG_ENGINE` | RAG 引擎模式 | `rag_lab`（增强引擎）、`legacy`（原始流程） |
| `CHUNK_STRATEGY` | 分块策略 | `semantic` / `paragraph` / `recursive` / `sentence_window` / `markdown_header` |
| `RAG_RETRIEVAL_MODE` | 检索模式 | `vector` / `keyword` / `hybrid` |
| `RAG_HYBRID_FUSION` | 混合融合方式 | `rrf` / `weighted_score` |
| `RAG_USE_RERANK` | 是否启用 Rerank | `true` / `false` |
| `RAG_RERANK_TOP_N` | Rerank 保留数量 | 整数，例如 `5` |

### LLM / Embedding

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | Chat 模型 API Key |
| `LLM_BASE_URL` | Chat 模型 API Base URL |
| `LLM_MODEL` / `CHAT_MODEL` | Chat 模型名称 |
| `LLM_TEMPERATURE` | 生成温度（默认 `0.1`） |
| `LLM_MAX_TOKENS` | 最大生成 token 数 |
| `EMBEDDING_API_KEY` | Embedding 模型 API Key |
| `EMBEDDING_API_BASE` | Embedding 模型 API Base URL |
| `EMBED_MODEL` / `EMBEDDING_MODEL_NAME` | Embedding 模型名称 |
| `EMBEDDING_DIM` | 向量维度（默认 `1024`） |
| `EMBEDDING_BATCH_SIZE` | Embedding 批大小 |

### 检索参数

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TOP_K` | 最终返回 chunk 数量 | `5` |
| `VECTOR_TOP_K` | 向量检索候选数 | `20` |
| `BM25_TOP_K` | BM25 检索候选数 | `20` |
| `HYBRID_TOP_K` | 混合检索候选数 | `30` |
| `SIMILARITY_SCORE_THRESHOLD` | 相似度过滤阈值 | `0.35` |
| `MIN_SOURCE_COUNT` | 最小引用数量 | `1` |

### 可选 Reranker

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | DashScope API Key |
| `ENABLE_RERANKER` | 是否启用外部 Reranker |
| `RERANKER_PROVIDER` | Reranker 提供商（`dashscope`） |
| `RERANKER_MODEL` | Reranker 模型名 |
| `RERANKER_TOP_K` | 送入 Reranker 的候选数 |
| `RERANKER_TOP_N` | Reranker 输出数量 |
| `RERANKER_SCORE_THRESHOLD` | Reranker 分数阈值 |

## RAG 引擎说明

### rag_lab（增强引擎）

使用 `backend/rag_lab/yuxi_rag/` 中的模块，完成完整的 RAG 流水线：

```
文档上传 → 文本解析 → 分块（Chunking）→ Embedding → 本地向量索引
                                                              ↓
LLM 回答 ← 上下文注入 ← Rerank（可选）← Hybrid Search（向量 + BM25）
```

优点：
- 纯本地 numpy 向量索引，零外部向量数据库依赖
- 混合检索提升召回率
- 可选 Rerank 提升精度
- 所有参数可通过环境变量配置

### legacy（原始引擎）

保留传统的 Milvus Lite + BM25 检索路径，兼容旧版部署，可在 `.env` 中通过 `RAG_ENGINE=legacy` 切换。

## 前端使用指南

前端提供五个主要视图，通过左侧导航栏切换：

| 视图 | 功能 |
|------|------|
| **总览** | 系统统计卡片、RAG 流水线状态、快速开始入口 |
| **知识库** | 创建/删除知识库，选择当前工作知识库 |
| **文档管理** | 上传文档、查看文档列表与索引状态、重建索引 |
| **智能问答** | 基于知识库的流式问答，引用溯源，会话管理 |
| **RAG 引擎** | 查看引擎配置、检索流程与当前知识库索引状态 |

问答结果中的 **引用溯源卡片** 包含：
- 来源文件名
- 分块策略标签
- 综合分数（score）
- 内容摘要
- 可折叠的高级分数：dense_score、sparse_score、fusion_score、rerank_score

## 评估

### 基础检索评估

```bash
# Smoke 测试
python backend/rag_lab/eval/smoke_test_main_rag.py

# 参数扫描实验
python backend/rag_lab/eval/run_param_experiments.py
```

输出指标：Hit@K、Recall@K、MRR、keyword_hit。

### Ragas 评估（可选）

```bash
pip install -r backend/rag_lab/requirements-rag-lab.txt
python backend/rag_lab/eval/run_ragas_eval.py --skip-ragas
```

> 评估报告默认被 gitignore，不会提交到仓库。

## 开源注意事项

请勿提交以下内容：

- `.env` 或任何包含 API Key 的文件
- `.venv/`、`venv/`、`node_modules/`
- 前端 `dist/`、`build/`
- 真实上传的文档文件
- 生成的向量索引与 chunk 缓存（`backend/rag_lab/data/`）
- 评估报告（`*report*.json`、`*report*.md`）
- 本地运行缓存：`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`

仓库应仅保留源码、脱敏配置示例和可复现脚本。

## License

MIT
