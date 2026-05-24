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
        if settings.MILVUS_HOST:
            uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
            self._client = MilvusClient(uri=uri)
        else:
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
                            document_name: str, chunk_indices: list[int], doc_id: str = "",
                            section_titles: list[str] | None = None,
                            section_paths: list[str] | None = None,
                            pages: list[int | None] | None = None,
                            chunk_strategies: list[str] | None = None) -> list[int]:
        client = await self.connect()
        name = self._collection_name(kb_id)
        data = []
        for i, (e, t) in enumerate(zip(embeddings, texts)):
            record = {
                "vector": e,
                "text": t,
                "document_name": document_name,
                "chunk_index": chunk_indices[i] if i < len(chunk_indices) else i,
                "doc_id": doc_id,
            }
            if section_titles and i < len(section_titles):
                record["section_title"] = section_titles[i] or ""
            if section_paths and i < len(section_paths):
                record["section_path"] = section_paths[i] or ""
            if pages and i < len(pages) and pages[i] is not None:
                record["page"] = pages[i]
            if chunk_strategies and i < len(chunk_strategies):
                record["chunk_strategy"] = chunk_strategies[i] or ""
            data.append(record)

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
                output_fields=[
                    "text", "document_name", "chunk_index", "chunk_strategy",
                    "section_title", "section_path", "page", "doc_id",
                ],
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
                "section_title": entity.get("section_title", ""),
                "section_path": entity.get("section_path", ""),
                "page": entity.get("page"),
                "doc_id": entity.get("doc_id", ""),
                "chunk_strategy": entity.get("chunk_strategy", ""),
                "score": float(hit.get("distance", 0)),
            })
        return hits

    async def get_all_chunks(self, kb_id: str, batch_size: int = 1000) -> list[dict]:
        """Retrieve all chunk entities (text + metadata) from a collection.

        Used by BM25 index builder to get the full corpus.
        """
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            return []

        await self.load_collection(kb_id)

        all_entities = []
        offset = 0
        output_fields = [
            "text", "document_name", "chunk_index", "chunk_strategy",
            "section_title", "section_path", "page", "doc_id",
        ]

        def _query_page(_offset, _limit):
            return client.query(
                collection_name=name,
                filter="id >= 0",
                output_fields=output_fields,
                limit=_limit,
                offset=_offset,
            )

        while True:
            page = await asyncio.get_event_loop().run_in_executor(
                None, _query_page, offset, batch_size)
            if not page:
                break
            for entity in page:
                all_entities.append({
                    "id": entity.get("id"),
                    "content": entity.get("text", ""),
                    "document_name": entity.get("document_name", ""),
                    "chunk_index": entity.get("chunk_index", 0),
                    "section_title": entity.get("section_title", ""),
                    "section_path": entity.get("section_path", ""),
                    "page": entity.get("page"),
                    "doc_id": entity.get("doc_id", ""),
                    "chunk_strategy": entity.get("chunk_strategy", ""),
                })
            if len(page) < batch_size:
                break
            offset += batch_size

        return all_entities

    async def delete_document_chunks(self, kb_id: str, doc_id: str) -> int:
        """Delete all chunks belonging to *doc_id* from Milvus.

        Returns the number of entities deleted.
        """
        import logging
        logger = logging.getLogger(__name__)
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            logger.info("[Milvus] kb=%s doc=%s — collection not found, skip delete", kb_id, doc_id)
            return 0

        def _delete():
            result = client.delete(collection_name=name, filter=f'doc_id == "{doc_id}"')
            return result

        result = await asyncio.get_event_loop().run_in_executor(None, _delete)
        count = result.get("delete_count", 0) if isinstance(result, dict) else 0
        logger.info("[Milvus] kb=%s doc=%s deleted_count=%d", kb_id, doc_id, count)
        return count

    async def delete_knowledge_base_chunks(self, kb_id: str) -> int:
        """Delete ALL chunks for a knowledge base without dropping the collection.

        Returns the number of entities deleted.  Returns 0 if the collection
        does not exist (idempotent).
        """
        import logging
        logger = logging.getLogger(__name__)
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            logger.info("[Milvus] kb=%s — collection not found, skip delete", kb_id)
            return 0

        def _delete():
            result = client.delete(collection_name=name, filter="id >= 0")
            return result

        result = await asyncio.get_event_loop().run_in_executor(None, _delete)
        count = result.get("delete_count", 0) if isinstance(result, dict) else 0
        logger.info("[Milvus] kb=%s deleted_all_count=%d", kb_id, count)
        return count

    async def count_chunks(self, kb_id: str) -> int:
        """Return the number of chunks in a knowledge base collection."""
        client = await self.connect()
        name = self._collection_name(kb_id)
        if not client.has_collection(name):
            return 0
        await self.load_collection(kb_id)

        def _count():
            # Use a lightweight query to count entities
            stats = client.get_collection_stats(name)
            return stats.get("row_count", 0)

        return await asyncio.get_event_loop().run_in_executor(None, _count)


milvus_client = MilvusClientWrapper()
