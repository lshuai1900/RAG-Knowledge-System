# RAG Knowledge System

基于 RAG（检索增强生成）的知识库问答系统。上传文档构建知识库，通过自然语言提问，系统自动检索相关内容并结合 DeepSeek 大模型生成精准回答。

## 技术栈

| 层级 | 技术 |
|------|------|
| **RAG 框架** | LangChain + LangGraph |
| **后端** | FastAPI (Python)，异步 SSE 流式响应 |
| **向量数据库** | Milvus Lite（嵌入式，零配置） |
| **大模型** | DeepSeek，通过 LangChain OpenAI 兼容接口 |
| **嵌入模型** | 阿里 DashScope text-embedding-v3（兼容 OpenAI API，无需 GPU） |
| **前端** | React 19 + TypeScript + Vite + Tailwind CSS 4 |
| **数据库** | SQLite（aiosqlite 异步驱动） |

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，lifespan 管理
│   │   ├── config.py            # pydantic-settings 配置
│   │   ├── api/
│   │   │   ├── router.py        # 路由聚合
│   │   │   └── endpoints/       # health / knowledge_base / document / chat
│   │   ├── services/
│   │   │   ├── embedding_service.py   # 嵌入 API 封装 (DashScope)
│   │   │   ├── llm_service.py         # DeepSeek LLM 封装
│   │   │   ├── document_service.py    # 文档加载与分块
│   │   │   ├── ingestion_service.py   # 文档摄入编排（后台任务）
│   │   │   ├── retrieval_service.py   # Milvus 相似度检索
│   │   │   ├── rag_service.py         # RAG 全流程编排
│   │   │   ├── chat_history_service.py # 对话历史管理
│   │   │   └── knowledge_base_service.py # 知识库 CRUD
│   │   ├── db/
│   │   │   ├── milvus_client.py    # Milvus Lite 连接管理
│   │   │   └── sqlite_database.py  # SQLite 表结构与操作
│   │   ├── models/              # Pydantic 请求/响应模型
│   │   └── core/                # 异常处理、依赖注入
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Chat / Document / KnowledgeBase / Layout
│   │   ├── hooks/               # useStreamChat (SSE 流式读取)
│   │   ├── store/               # Zustand 状态管理
│   │   ├── api/                 # Axios API 客户端
│   │   └── types/               # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
```

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+
- DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com)）
- 阿里 DashScope API Key（用于嵌入模型，[dashscope.aliyun.com](https://dashscope.aliyun.com)）

### 1. 后端配置

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 编辑 .env，填入 API Key
# DEEPSEEK_API_KEY=sk-xxx    （必填）
# EMBEDDING_API_KEY=sk-xxx   （必填）
```

### 2. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 http://localhost:8000，API 文档 http://localhost:8000/docs

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

前端运行在 http://localhost:5173（Vite 代理 `/api` → `localhost:8000`）

### 4. 使用

1. 打开 http://localhost:5173
2. 左侧创建知识库
3. 上传文档（PDF / TXT / Markdown / DOCX）
4. 等待文档就绪（绿色勾）
5. 右侧聊天框提问

## API

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
| PUT | `/api/v1/knowledge-bases/{kb_id}` | 更新 |
| DELETE | `/api/v1/knowledge-bases/{kb_id}` | 删除（含文档与向量） |

### 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge-bases/{kb_id}/documents/upload` | 上传文档（multipart） |
| GET | `/api/v1/knowledge-bases/{kb_id}/documents` | 列出文档 |
| GET | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/status` | 查询摄入状态 |
| DELETE | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}` | 删除文档及向量 |

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions` | 创建会话 |
| GET | `/api/v1/chat/sessions` | 列出会话（`?kb_id=` 过滤） |
| GET | `/api/v1/chat/sessions/{session_id}` | 会话详情 + 消息历史 |
| DELETE | `/api/v1/chat/sessions/{session_id}` | 删除会话 |
| POST | `/api/v1/chat/query` | 非流式查询 |
| POST | `/api/v1/chat/query/stream` | 流式查询（SSE） |

### SSE 流式事件

```
event: chunk
data: {"text": "部分回答..."}

event: sources
data: {"sources": [{"content": "...", "document_name": "file.pdf", "chunk_index": 0, "score": 0.93}]}

event: done
data: {"message_id": "msg_xxx"}
```

## 支持的文件格式

| 格式 | 扩展名 | 加载器 |
|------|--------|--------|
| PDF | `.pdf` | PyPDFLoader |
| 纯文本 | `.txt` | TextLoader |
| Markdown | `.md` | TextLoader |
| Word | `.docx` | Docx2txtLoader |

## 环境变量

### 大模型

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填**，DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com/v1` | API 端点 |
| `DEEPSEEK_MODEL_NAME` | `deepseek-chat` | 模型名称 |
| `LLM_TEMPERATURE` | `0.1` | 温度参数 |
| `LLM_MAX_TOKENS` | `4096` | 最大生成 Token |

### 嵌入模型

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_API_KEY` | — | **必填**，DashScope API 密钥 |
| `EMBEDDING_API_BASE` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 端点（兼容 OpenAI 格式） |
| `EMBEDDING_MODEL_NAME` | `text-embedding-v3` | 嵌入模型名称 |
| `EMBEDDING_DIM` | `1024` | 向量维度（须匹配模型） |

### 文档处理

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_SIZE` | `1000` | 文档分块大小（字符数） |
| `CHUNK_OVERLAP` | `200` | 分块重叠字符数 |
| `MAX_UPLOAD_SIZE_MB` | `50` | 单文件上传上限 |
| `UPLOAD_DIR` | `./data/uploads` | 上传文件存储路径 |

### 数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MILVUS_DB_PATH` | `./data/milvus.db` | Milvus Lite 向量数据路径 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/rag.db` | SQLite 数据库连接 |
| `SQLITE_PATH` | `./data/rag.db` | SQLite 文件路径 |

### 检索

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TOP_K` | `5` | 检索返回最大文档片段数 |
| `MAX_HISTORY_TURNS` | `10` | 对话历史保留轮数 |

## 架构

### 文档摄入流程

```
上传文件 → 保存到磁盘 → 异步后台任务
                        ├── LangChain 加载文档
                        ├── 递归文本分块
                        ├── API 生成嵌入向量 (DashScope)
                        ├── 插入 Milvus 集合
                        └── 更新状态: pending → processing → ready
```

### RAG 问答流程

```
用户提问 → API 生成查询嵌入 → Milvus 检索 Top-K → 构建 System Prompt
                                                → 加载对话历史
                                                → DeepSeek 流式生成
                                                → 保存消息 → 返回来源
```

### 数据存储

- **SQLite** (`data/rag.db`) — 知识库、文档、会话、消息元数据
- **Milvus Lite** (`data/milvus.db`) — 文档向量与文本，单文件嵌入式存储
- **本地磁盘** (`data/uploads/`) — 原始上传文件

## 手动启动

项目使用 Milvus Lite 嵌入式模式，无需 Docker，直接运行即可。

### 后端

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt   # 首次运行
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 http://localhost:8000，API 文档 http://localhost:8000/docs

### 前端

```bash
cd frontend
npm install                       # 首次运行
npm run dev -- --host 0.0.0.0 --port 5173
```

前端运行在 http://localhost:5173（Vite 代理 `/api` → `localhost:8000`）

## License

MIT
