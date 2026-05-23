# Yuxi-RAG 实验模块

`backend/rag_lab` 是一个独立的 RAG 实验区，用来验证 Yuxi 项目中的模块化 RAG 思路：文档解析、段落优先分块、本地 numpy 向量索引、Top-K/MMR 召回、可选 Reranker、生成与评估。

该模块只通过命令行运行，不挂载线上 API，不修改现有 `query` / `query_stream` 主流程、前端、Hybrid Search、Reranker、低置信度拒答逻辑或 Docker 配置。

## 1. 目录结构

```text
backend/rag_lab/
├── yuxi_rag/
│   ├── loader.py
│   ├── parser.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── generator.py
│   └── pipeline.py
├── eval/
│   ├── eval_questions.json
│   ├── run_yuxi_rag_eval.py
│   ├── run_param_experiments.py
│   ├── run_ragas_eval.py
│   └── smoke_test_main_rag.py
└── data/
    ├── docs/
    ├── index/
    └── chunks/
```

## 2. 配置

Embedding 和 LLM 都使用 OpenAI-compatible API。

优先读取：

```env
EMBED_MODEL=your-embedding-model
LLM_API_KEY=
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-chat-model
```

如果没有配置上述变量，会尝试复用当前项目 `.env` 中已有的：

```env
EMBEDDING_MODEL_NAME=your-embedding-model
EMBEDDING_API_KEY=
EMBEDDING_API_BASE=https://api.example.com/v1
DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE=https://api.example.com/v1
DEEPSEEK_MODEL_NAME=your-chat-model
```

脚本不会写死或打印 API Key。

## 3. 放入实验文档

把文档放到：

```text
backend/rag_lab/data/docs/
```

支持格式：

- `.txt`
- `.md`
- `.pdf`
- `.docx`

目录中已经包含一个最小示例：`01_RAG_intro.md`，用于首次验证命令是否能跑通。

## 4. 构建本地索引

在仓库根目录执行：

```bash
python backend/rag_lab/yuxi_rag/pipeline.py --build-index
```

可调整分块参数：

```bash
python backend/rag_lab/yuxi_rag/pipeline.py \
  --build-index \
  --chunk-size 800 \
  --chunk-overlap 120
```

输出文件：

- `backend/rag_lab/data/chunks/chunks.json`
- `backend/rag_lab/data/index/embeddings.npy`
- `backend/rag_lab/data/index/metadata.json`

## 5. 提问

```bash
python backend/rag_lab/yuxi_rag/pipeline.py --ask "RAG 是什么？" --top-k 5
```

只看召回，不调用 LLM：

```bash
python backend/rag_lab/yuxi_rag/pipeline.py \
  --ask "RAG 是什么？" \
  --top-k 5 \
  --retrieval-only
```

启用 MMR：

```bash
python backend/rag_lab/yuxi_rag/pipeline.py \
  --ask "RAG 为什么要优化分块？" \
  --top-k 5 \
  --use-mmr \
  --lambda-mult 0.5
```

尝试复用当前项目 Reranker：

```bash
python backend/rag_lab/yuxi_rag/pipeline.py \
  --ask "RAG 是什么？" \
  --top-k 5 \
  --use-reranker
```

如果当前项目未启用 Reranker 或依赖不可用，该参数会自动跳过，不会报错。

## 6. 运行评估

```bash
python backend/rag_lab/eval/run_yuxi_rag_eval.py \
  --questions backend/rag_lab/eval/eval_questions.json \
  --output-json backend/rag_lab/eval/eval_report.json \
  --output-md backend/rag_lab/eval/eval_report.md \
  --top-k 5
```

只评估召回：

```bash
python backend/rag_lab/eval/run_yuxi_rag_eval.py \
  --questions backend/rag_lab/eval/eval_questions.json \
  --retrieval-only \
  --top-k 5
```

跳过 Ragas，只输出基础指标和问答结果：

```bash
python backend/rag_lab/eval/run_yuxi_rag_eval.py \
  --questions backend/rag_lab/eval/eval_questions.json \
  --skip-ragas \
  --top-k 5
```

常用参数：

- `--limit`：限制评估问题数量。
- `--top-k`：计算 Hit@K、Recall@K、MRR 的 K 值。
- `--retrieval-only`：只跑检索，不生成答案。
- `--skip-ragas`：生成答案，但跳过 Ragas。
- `--run-name`：指定评估名称。
- `--use-mmr` / `--lambda-mult`：评估 MMR 召回。
- `--use-reranker`：尝试评估可选 Reranker。

报告输出：

- `backend/rag_lab/eval/eval_report.json`
- `backend/rag_lab/eval/eval_report.md`

## 7. 如何把有效策略迁移回主 RAG 流程

建议先在实验模块中做参数和策略对比，不要直接改线上流程：

1. 在 `backend/rag_lab/yuxi_rag/chunker.py` 中调整段落合并、长段切分、`chunk_size`、`chunk_overlap`。
2. 用 `run_yuxi_rag_eval.py` 对比 Hit@K、Recall@K、MRR、Ragas 指标和单题结果。
3. 找到稳定收益后，再把分块策略迁移到主流程的 `backend/app/services/semantic_chunker.py` 或 `backend/app/services/document_service.py`。
4. 用现有主流程评估脚本 `backend/eval/run_auto_eval.py` 回归验证，确认没有破坏 Hybrid Search、Reranker、低置信度拒答和前端引用展示。
5. 最后再考虑接入线上入库流程；不要把 `rag_lab` 直接挂到 API router。
