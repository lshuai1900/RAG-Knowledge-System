# RAG Knowledge System

RAG Knowledge System 是一个面向知识库问答的开源 RAG（Retrieval-Augmented Generation，检索增强生成）系统。项目集成了文档上传与解析、多策略分块、OpenAI-compatible Embedding、本地向量索引、Hybrid Search、可选 Rerank、LLM 问答、Ragas / 基础自动评估、前端 RAG 状态可视化，以及 legacy 回滚机制。

## 功能特性

- 知识库管理、文档上传、文档解析、索引重建。
- 分块策略：`semantic`、`paragraph`、`recursive`、`sentence_window`、`markdown_header`。
- 检索模式：`vector`、`keyword`、`hybrid`。
- 融合方式：`rrf`、`weighted_score`。
- 可选 Rerank，并支持配置 `RAG_RERANK_TOP_N`。
- `rag_lab` 增强 RAG 引擎：本地 numpy 向量索引、混合检索、可选重排。
- `legacy` 原始流程回滚机制，便于保留旧版后端 RAG 路径。
- 自动评估脚本：Hit@K、Recall@K、MRR、keyword_hit，以及可选 Ragas 指标。
- 前端 RAG 引擎状态面板，可展示当前配置和 RAG 流程。
- 问答 sources 卡片展示：`score`、`dense_score`、`sparse_score`、`fusion_score`、`rerank_score`、`chunk_strategy`。

## 技术栈

- Backend：FastAPI / Python
- Frontend：React / Vite / TypeScript
- Vector index：local numpy index
- RAG eval：optional Ragas
- LLM / Embedding：OpenAI-compatible API
- Legacy vector path：Milvus Lite / Milvus-compatible path

## 项目结构

```text
.
├── backend/
│   ├── app/                         # FastAPI 主应用、API、服务层、模型、数据库适配
│   ├── rag_lab/                     # 增强 RAG 实验引擎与评估脚本
│   │   ├── yuxi_rag/                # loader / chunker / retriever / hybrid search / reranker / generator
│   │   ├── eval/                    # smoke、参数实验、Ragas / 基础评估脚本
│   │   └── data/                    # 运行时 docs/chunks/index；生成物默认忽略
│   └── requirements.txt             # 主后端依赖
├── frontend/
│   └── src/                         # React 前端源码、组件、API、hooks、store、types
├── docker-compose.yml               # 可选本地编排文件
├── .env.example                     # 脱敏环境变量示例
└── README.md
```

## 快速开始

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd RAG-Knowledge-System
```

### 2. 创建 Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. 安装后端依赖

```bash
pip install -r backend/requirements.txt
```

### 4. 安装 rag_lab / 评估可选依赖

如果需要运行 `backend/rag_lab` 实验、参数评估或 Ragas 评估，再安装：

```bash
pip install -r backend/rag_lab/requirements-rag-lab.txt
```

### 5. 安装前端依赖

```bash
npm --prefix frontend install
```

### 6. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你自己的 OpenAI-compatible Chat / Embedding 服务配置。不要提交 `.env`。

### 7. 启动后端

```bash
PYTHONPATH=backend RAG_ENGINE=rag_lab DEBUG=false \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端地址：

- API 根地址：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- RAG 状态接口：`http://localhost:8000/api/v1/rag/status`

### 8. 启动前端

```bash
npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
```

前端页面：

- `http://localhost:5173`

## 环境变量说明

增强 RAG 流程的常用配置：

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

更多后端变量请参考 [.env.example](.env.example)，包括：

- `DATABASE_URL`
- `UPLOAD_DIR`
- `SIMILARITY_SCORE_THRESHOLD`
- `TOP_K`
- legacy Milvus / BM25 配置
- Reranker 配置

## RAG 模式说明

### `RAG_ENGINE=rag_lab`

增强 RAG 引擎。该模式使用 [backend/rag_lab/yuxi_rag/](backend/rag_lab/yuxi_rag/) 中的模块完成文档加载、分块、本地向量索引、向量 / 关键词 / 混合检索、可选 rerank 和答案生成。

常用参数：

- `CHUNK_STRATEGY`：`semantic`、`paragraph`、`recursive`、`sentence_window`、`markdown_header`
- `RAG_RETRIEVAL_MODE`：`vector`、`keyword`、`hybrid`
- `RAG_HYBRID_FUSION`：`rrf`、`weighted_score`
- `RAG_USE_RERANK`：`true` / `false`
- `RAG_RERANK_TOP_N`：rerank 后保留的 chunk 数量

### `RAG_ENGINE=legacy`

原始后端 RAG 流程。该模式保留旧版 Milvus / BM25 服务路径，可作为线上回滚机制或兼容旧部署使用。

## 评估脚本说明

在仓库根目录执行，运行前请安装依赖并配置 `.env`：

```bash
python backend/rag_lab/eval/smoke_test_main_rag.py
python backend/rag_lab/eval/run_param_experiments.py
python backend/rag_lab/eval/run_ragas_eval.py --skip-ragas
```

评估脚本支持基础检索指标：

- Hit@K
- Recall@K
- MRR
- keyword_hit

Ragas 是可选评估能力，相关依赖放在 [backend/rag_lab/requirements-rag-lab.txt](backend/rag_lab/requirements-rag-lab.txt)，不强制主后端流程安装。

生成的评估报告默认被 git 忽略：

- `backend/rag_lab/eval/*report*.json`
- `backend/rag_lab/eval/*report*.md`

## 前端展示说明

前端在知识库 / 文档区域提供 RAG 引擎状态面板，用于展示：

- 当前引擎：`rag_lab` / `legacy`
- 分块策略
- 检索模式
- 融合方式
- Rerank 开关
- Rerank Top N
- 流程展示：文档上传 → 分块 → Embedding → Hybrid Search → Rerank → LLM 回答

问答结果中的 sources 使用卡片展示：

- source 文件名
- chunk strategy 标签
- 总分 `score`
- 上下文摘要
- 可折叠高级分数：`dense_score`、`sparse_score`、`fusion_score`、`rerank_score`

## 开源注意事项

不要提交本地运行文件或敏感信息：

- `.env` 或任何包含 API Key 的文件
- `.venv/`、`venv/`
- `node_modules/`
- 前端 `dist/`、`build/`
- 真实上传文档
- 生成的向量索引和 chunks
- 生成的评估报告
- 本地缓存：`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`

仓库应只保留源码、脱敏配置示例、示例文档和可复现脚本。

## License

License: MIT recommended. Please add LICENSE before publishing.
