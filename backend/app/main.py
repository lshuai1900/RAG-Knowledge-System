import os
from app.config import settings

# Set HuggingFace mirror BEFORE any other imports that may load models
if settings.HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Recover stuck documents from previous crash
    from app.db.sqlite_database import get_database
    db = await get_database()
    await db.execute(
        "UPDATE documents SET status = 'failed', error_message = 'Server restarted during ingestion' WHERE status IN ('pending', 'processing')"
    )
    await db.commit()

    # Warm up embedding model at startup so first upload is fast
    from app.services.embedding_service import embedding_service
    await embedding_service._get_model()

    yield
    # Shutdown: close connections
    from app.db.milvus_client import milvus_client
    from app.db.sqlite_database import close_database
    await milvus_client.disconnect()
    await close_database()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
register_exception_handlers(app)
