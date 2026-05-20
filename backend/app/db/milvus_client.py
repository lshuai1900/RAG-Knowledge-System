import asyncio
import milvus_lite
from pymilvus import MilvusClient
from app.config import settings


class MilvusClientWrapper:
    def __init__(self):
        self.dim = settings.EMBEDDING_DIM
        self.db_path = settings.MILVUS_DB_PATH
        self._client: MilvusClient | None = None

    def _connect_sync(self) -> MilvusClient:
        if self._client is not None:
            return self._client
        sm = milvus_lite.server_manager.server_manager_instance
        uri = sm.start_and_get_uri(self.db_path)
        if uri is None:
            raise RuntimeError(f"Failed to start Milvus Lite server for {self.db_path}")
        self._client = MilvusClient(uri=uri)
        return self._client

    async def connect(self):
        return await asyncio.get_event_loop().run_in_executor(None, self._connect_sync)

    async def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None

    def _collection_name(self, kb_id: str) -> str:
        return f"kb_{kb_id}"

    async def create_collection(self, kb_id: str):
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.create_collection(
                    collection_name=name,
                    dimension=self.dim,
                    metric_type="COSINE",
                    auto_id=True,
                )
            )

    async def drop_collection(self, kb_id: str):
        client = await self.connect()
        name = self._collection_name(kb_id)
        if client.has_collection(name):
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.drop_collection(name)
            )

    async def load_collection(self, kb_id: str):
        client = await self.connect()
        name = self._collection_name(kb_id)
        if client.has_collection(name):
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.load_collection(name)
            )

    async def insert_chunks(self, kb_id: str, texts: list[str], embeddings: list[list[float]],
                            document_name: str, chunk_indices: list[int]) -> list[int]:
        client = await self.connect()
        name = self._collection_name(kb_id)
        data = [{"vector": e, "text": t, "document_name": document_name, "chunk_index": i}
                for e, t, i in zip(embeddings, texts, chunk_indices)]

        def _insert():
            return client.insert(collection_name=name, data=data)
        result = await asyncio.get_event_loop().run_in_executor(None, _insert)
        await self.load_collection(kb_id)
        return result["ids"]

    async def search(self, kb_id: str, query_vector: list[float], top_k: int) -> list[dict]:
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            return []

        await self.load_collection(kb_id)

        def _search():
            return client.search(
                collection_name=name, data=[query_vector], limit=top_k,
                output_fields=["text", "document_name", "chunk_index"],
            )
        results = await asyncio.get_event_loop().run_in_executor(None, _search)

        hits = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            hits.append({
                "id": hit["id"],
                "content": entity.get("text", ""),
                "document_name": entity.get("document_name", ""),
                "chunk_index": entity.get("chunk_index", 0),
                "score": float(hit.get("distance", 0)),
            })
        return hits

    async def delete_document_chunks(self, kb_id: str, document_name: str):
        client = await self.connect()
        name = self._collection_name(kb_id)
        if client.has_collection(name):
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.delete(collection_name=name, filter=f'document_name == "{document_name}"')
            )


milvus_client = MilvusClientWrapper()
