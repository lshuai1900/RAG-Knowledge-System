from openai import AsyncOpenAI
from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str, api_key: str, base_url: str | None = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def embed_query(self, text: str) -> list[float]:
        client = self._get_client()
        response = await client.embeddings.create(model=self.model_name, input=text)
        return response.data[0].embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        # DashScope limits batch size to 10
        batch_size = 10
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await client.embeddings.create(model=self.model_name, input=batch)
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings


embedding_service = EmbeddingService(
    model_name=settings.EMBEDDING_MODEL_NAME,
    api_key=settings.EMBEDDING_API_KEY,
    base_url=settings.EMBEDDING_API_BASE,
)
