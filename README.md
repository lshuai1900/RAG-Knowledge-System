# RAG Knowledge System

基于 RAG（Retrieval-Augmented Generation）的知识库智能问答系统。上传文档构建知识库，通过自然语言提问，系统自动检索相关内容并结合 DeepSeek 大模型生成精准回答。

## 技术栈

| 层级 | 技术 |
|------|------|
| **RAG 框架** | LangChain |
| **后端** | FastAPI (Python)，异步 SSE 流式响应 |
| **向量数据库** | Milvus Lite（嵌入式，无需 Docker） |
| **大模型** | DeepSeek (`deepseek-chat`)，通过 LangChain OpenAI 兼容接口 |
| **嵌入模型** | BAAI/bge-small-zh-v1.5（512维，24MB，本地加载） |
| **前端** | React 19 + TypeScript + Vite + Tailwind CSS 4 |
| **数据库** | SQLite（aiosqlite 异步驱动） |

## 项目结构

```
RAG-Knowledge-System/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，lifespan 管理
│   │   ├── config.py            # pydantic-settings 配置
│   │   ├── api/
│   │   │   ├── router.py        # 路由聚合
│   │   │   └── endpoints/       # health / knowledge_base / document / chat
│   │   ├── services/
│   │   │   ├── embedding_service.py   # 嵌入模型封装 (sentence-transformers)
│   │   │   ├── llm_service.py         # DeepSeek LLM 封装 (ChatOpenAI)
│   │   │   ├── document_service.py    # 文档加载与分块
│   │   │   ├── ingestion_service.py   # 文档摄入编排（异步后台任务）
│   │   │   ├── retrieval_service.py   # Milvus 相似度检索
│   │   │   ├── rag_service.py         # RAG 全流程编排 (检索 + 历史 + LLM)
│   │   │   ├── chat_history_service.py # 对话历史管理
│   │   │   └── knowledge_base_service.py # 知识库 CRUD
│   │   ├── db/
│   │   │   ├── milvus_client.py    # Milvus Lite 连接管理
│   │   │   └── sqlite_database.py  # SQLite 表结构与操作
│   │   ├── models/              # Pydantic 请求/响应模型
│   │   └── core/                # 异常处理、依赖注入
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/            # ChatPanel, MessageList, MessageBubble, ChatInput,
│   │   │   │                      SourceCitation, ChatSessionList
│   │   │   ├── Document/        # DocumentUploader, DocumentList, DocumentManager
│   │   │   ├── KnowledgeBase/   # KnowledgeBaseList, KnowledgeBaseForm
│   │   │   └── Layout/          # AppLayout, Sidebar
│   │   ├── hooks/               # useStreamChat (SSE 流式读取)
│   │   ├── store/               # Zustand 全局状态管理
│   │   ├── api/                 # Axios API 客户端
│   │   └── types/               # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
├── docker/                      # Docker Compose 配置（可选）
├── .env.example                 # 环境变量模板
└── README.md
```

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+
- DeepSeek API Key（在 [DeepSeek 平台](https://platform.deepseek.com) 获取）

### 1. 后端配置

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 2. 启动后端

```bash
# 从 backend 目录运行
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 http://localhost:8000，OpenAPI 文档在 http://localhost:8000/docs

### 3. 启动前端

```bash
cd frontend

npm install
npm run dev
```

前端运行在 http://localhost:5173（Vite 已配置 API 代理到后端 8000 端口）

### 4. 使用

1. 打开 http://localhost:5173
2. 点击左侧"新建知识库"创建知识库
3. 上传文档（PDF、TXT、Markdown、DOCX）
4. 等待文档状态变为绿色勾（就绪）
5. 在右侧聊天框输入问题，开始问答

## API 概览

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 服务健康状态 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge-bases` | 列出所有知识库 |
| POST | `/api/v1/knowledge-bases` | 创建知识库 |
| GET | `/api/v1/knowledge-bases/{kb_id}` | 获取详情 |
| PUT | `/api/v1/knowledge-bases/{kb_id}` | 更新知识库 |
| DELETE | `/api/v1/knowledge-bases/{kb_id}` | 删除知识库（含文档与向量） |

### 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge-bases/{kb_id}/documents/upload` | 上传文档（multipart 多文件） |
| GET | `/api/v1/knowledge-bases/{kb_id}/documents` | 列出文档 |
| GET | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/status` | 查询摄入状态 |
| DELETE | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}` | 删除文档及向量 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions` | 创建会话 |
| GET | `/api/v1/chat/sessions` | 列出会话（支持 ?kb_id= 过滤） |
| GET | `/api/v1/chat/sessions/{session_id}` | 获取会话详情 + 消息历史 |
| DELETE | `/api/v1/chat/sessions/{session_id}` | 删除会话及消息 |
| POST | `/api/v1/chat/query` | 非流式查询 |
| POST | `/api/v1/chat/query/stream` | 流式查询（SSE） |

### SSE 流式事件格式

```
event: chunk
data: {"text": "部分回答文本..."}

event: sources
data: {"sources": [{"content": "文档片段...", "document_name": "file.pdf", "chunk_index": 0, "score": 0.93}]}

event: done
data: {"message_id": "msg_xxx"}
```

## 支持的文件格式

| 格式 | 扩展名 | 加载器 |
|------|--------|--------|
| PDF | `.pdf` | PyPDFLoader |
| 纯文本 | `.txt` | TextLoader |
| Markdown | `.md` | TextLoader |
| Word | `.docx`, `.doc` | Docx2txtLoader |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填**，DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com/v1` | API 端点 |
| `DEEPSEEK_MODEL_NAME` | `deepseek-chat` | 模型名称 |
| `LLM_TEMPERATURE` | `0.1` | LLM 温度参数 |
| `LLM_MAX_TOKENS` | `4096` | 最大生成 Token 数 |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-small-zh-v1.5` | HuggingFace 嵌入模型 |
| `EMBEDDING_DIM` | `512` | 向量维度（须匹配模型） |
| `EMBEDDING_DEVICE` | `cpu` | 推理设备 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 镜像（国内加速） |
| `CHUNK_SIZE` | `1000` | 文档分块大小（字符数） |
| `CHUNK_OVERLAP` | `200` | 分块重叠字符数 |
| `TOP_K` | `5` | 检索返回最大文档数 |
| `MAX_HISTORY_TURNS` | `10` | 对话历史保留轮数 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 单文件上传上限 |
| `MILVUS_DB_PATH` | `./data/milvus.db` | Milvus Lite 数据路径 |
| `SQLITE_PATH` | `./data/rag.db` | SQLite 数据库路径 |
| `UPLOAD_DIR` | `./data/uploads` | 上传文件存储路径 |

## 架构说明

### 文档摄入流程

```
上传文件 → 保存文件 → 异步后台任务
                    ├── LangChain 加载文档
                    ├── 递归文本分块
                    ├── 生成嵌入向量 (sentence-transformers)
                    ├── 插入 Milvus 集合
                    └── 更新状态: pending → processing → ready
```

### RAG 问答流程

```
用户提问 → 生成查询嵌入 → Milvus 检索 Top-K → 构建 System Prompt
                                              → 加载对话历史
                                              → DeepSeek 流式生成
                                              → 保存消息 → 返回来源
```

### 数据存储

- **SQLite** (`data/rag.db`) — 知识库、文档、会话、消息元数据
- **Milvus Lite** (`data/milvus.db`) — 文档向量 + 文本，单文件嵌入式存储
- **本地磁盘** (`data/uploads/`) — 原始上传文件

## Docker 部署

项目使用 Milvus Lite 嵌入式模式，后端和前端可直接运行，无需 Docker。

需要容器化部署时可使用：

```bash
# 完整基础设施 (etcd + minio + milvus-standalone + backend + frontend)
docker compose -f docker/docker-compose.yml up --build

# 开发模式 (热重载)
docker compose -f docker/docker-compose.dev.yml up
```

## License

MIT
