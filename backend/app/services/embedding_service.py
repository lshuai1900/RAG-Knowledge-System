from langchain_openai import OpenAIEmbeddings
from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str, api_key: str, base_url: str | None = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self._model: OpenAIEmbeddings | None = None

    async def _get_model(self) -> OpenAIEmbeddings:
        if self._model is None:
            kwargs = {"model": self.model_name, "api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._model = OpenAIEmbeddings(**kwargs)
        return self._model

    async def embed_query(self, text: str) -> list[float]:
        model = await self._get_model()
        return await model.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = await self._get_model()
        return await model.aembed_documents(texts)


embedding_service = EmbeddingService(
    model_name=settings.EMBEDDING_MODEL_NAME,
    api_key=settings.EMBEDDING_API_KEY,
    base_url=settings.EMBEDDING_API_BASE,
)
