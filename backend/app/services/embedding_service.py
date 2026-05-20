import os
import asyncio
from sentence_transformers import SentenceTransformer
from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model: SentenceTransformer | None = None

    async def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            # Use HuggingFace mirror if configured
            mirror = getattr(settings, 'HF_ENDPOINT', None) or os.environ.get('HF_ENDPOINT')
            if mirror:
                os.environ['HF_ENDPOINT'] = mirror
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None, lambda: SentenceTransformer(self.model_name, device=self.device, trust_remote_code=settings.EMBEDDING_TRUST_REMOTE_CODE)
            )
        return self._model

    async def embed_query(self, text: str) -> list[float]:
        model = await self._get_model()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: model.encode(text, normalize_embeddings=True).tolist())
        return result

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = await self._get_model()
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        )
        return results


embedding_service = EmbeddingService(
    model_name=settings.EMBEDDING_MODEL_NAME,
    device=settings.EMBEDDING_DEVICE,
)
