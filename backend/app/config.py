from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # App
    APP_NAME: str = "RAG Knowledge System"
    DEBUG: bool = False

    # Milvus
    MILVUS_HOST: str = ""
    MILVUS_PORT: int = 19530
    MILVUS_DB_PATH: str = "./data/milvus.db"
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_DIM: int = 1536

    # DeepSeek LLM
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Embedding model (OpenAI-compatible API)
    EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"

    # Document chunking
    CHUNK_STRATEGY: str = "semantic"  # "semantic" | "recursive"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    MIN_CHUNK_SIZE: int = 100
    MAX_CHUNK_SIZE: int = 1500

    # Retrieval
    TOP_K: int = 5
    SIMILARITY_SCORE_THRESHOLD: float = 0.35  # cosine distance; <= this = relevant
    MIN_SOURCE_COUNT: int = 1  # minimum relevant sources before calling LLM
    ANSWER_WITHOUT_SOURCE: bool = False  # if False, refuse to answer when no relevant sources

    # Reranker (DashScope)
    DASHSCOPE_API_KEY: str = ""  # shared with embedding; fallback to EMBEDDING_API_KEY
    ENABLE_RERANKER: bool = False
    RERANKER_PROVIDER: str = "dashscope"
    RERANKER_MODEL: str = "gte-rerank-v2"
    RERANKER_TOP_K: int = 20  # how many chunks to recall from Milvus before reranking
    RERANKER_TOP_N: int = 5   # how many chunks to keep after reranking
    RERANKER_SCORE_THRESHOLD: float = 0.0  # optional minimum rerank score; 0 = disabled
    RERANKER_TIMEOUT: int = 30  # seconds

    # Chat history
    MAX_HISTORY_TURNS: int = 10

    # SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/rag.db"
    SQLITE_PATH: str = "./data/rag.db"

    # File storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50


settings = Settings()
