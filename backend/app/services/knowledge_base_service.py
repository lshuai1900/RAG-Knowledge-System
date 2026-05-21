import os
import asyncio
import shutil
import uuid
from datetime import datetime
from app.config import settings
from app.db.sqlite_database import get_database
from app.db.milvus_client import milvus_client


class KnowledgeBaseService:
    async def list_all(self) -> list[dict]:
        db = await get_database()
        cursor = await db.execute(
            """SELECT kb.*,
               (SELECT COUNT(*) FROM documents WHERE kb_id = kb.id) as document_count,
               (SELECT COALESCE(SUM(chunk_count), 0) FROM documents WHERE kb_id = kb.id) as chunk_count
            FROM knowledge_bases kb
            ORDER BY kb.created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_by_id(self, kb_id: str) -> dict | None:
        db = await get_database()
        cursor = await db.execute(
            """SELECT kb.*,
               (SELECT COUNT(*) FROM documents WHERE kb_id = kb.id) as document_count,
               (SELECT COALESCE(SUM(chunk_count), 0) FROM documents WHERE kb_id = kb.id) as chunk_count
            FROM knowledge_bases kb
            WHERE kb.id = ?""",
            (kb_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create(self, name: str, description: str) -> dict:
        kb_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat()
        db = await get_database()
        await db.execute(
            "INSERT INTO knowledge_bases (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (kb_id, name, description, now, now),
        )
        await db.commit()
        await milvus_client.create_collection(kb_id)
        return await self.get_by_id(kb_id)

    async def update(self, kb_id: str, name: str | None, description: str | None) -> dict | None:
        db = await get_database()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if updates:
            updates["updated_at"] = datetime.utcnow().isoformat()
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [kb_id]
            await db.execute(f"UPDATE knowledge_bases SET {set_clause} WHERE id = ?", values)
            await db.commit()
        return await self.get_by_id(kb_id)

    async def delete(self, kb_id: str) -> None:
        db = await get_database()
        await db.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
        await db.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        await db.commit()
        await milvus_client.drop_collection(kb_id)

        kb_dir = os.path.join(settings.UPLOAD_DIR, kb_id)
        if os.path.exists(kb_dir):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, shutil.rmtree, kb_dir)

        # Clean up BM25 index
        if settings.ENABLE_HYBRID_SEARCH:
            try:
                from app.services.bm25_service import bm25_service
                await bm25_service.delete_index(kb_id)
            except Exception:
                pass
