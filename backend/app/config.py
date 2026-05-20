from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # App
    APP_NAME: str = "RAG Knowledge System"
    DEBUG: bool = False

    # Milvus
    MILVUS_HOST: str = ""
    MILVUS_PORT: int = 19530
    MILVUS_DB_PATH: str = "./data/milvus.db"  # Path for Milvus Lite embedded DB
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_DIM: int = 512

    # DeepSeek LLM
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Embedding model
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_TRUST_REMOTE_CODE: bool = False
    HF_ENDPOINT: str = "https://hf-mirror.com"

    # Document chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Retrieval
    TOP_K: int = 5
    SIMILARITY_SCORE_THRESHOLD: float = 0.0

    # Chat history
    MAX_HISTORY_TURNS: int = 10

    # SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/rag.db"
    SQLITE_PATH: str = "./data/rag.db"

    # File storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50


settings = Settings()
