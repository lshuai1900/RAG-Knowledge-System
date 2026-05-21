import os
import asyncio
import logging
import shutil
import uuid
from datetime import datetime
from app.config import settings
from app.db.sqlite_database import get_database
from app.db.milvus_client import milvus_client

logger = logging.getLogger(__name__)


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

    async def delete(self, kb_id: str) -> dict:
        """Delete a knowledge base and all associated data.

        Steps:
          1. Count documents for reporting.
          2. Delete chat sessions and messages for this kb_id.
          3. Delete all document records.
          4. Delete the KB record.
          5. Drop the Milvus collection.
          6. Remove uploaded files.
          7. Remove BM25 index directory.

        Returns a result dict suitable for DeleteKnowledgeBaseResponse.
        """
        result = {
            "success": True,
            "kb_id": kb_id,
            "documents_deleted": 0,
            "milvus_deleted": False,
            "bm25_deleted": False,
            "warnings": [],
        }

        logger.info("[KB] Deleting knowledge base kb=%s", kb_id)

        db = await get_database()

        # Count documents before deletion
        cursor = await db.execute("SELECT COUNT(*) FROM documents WHERE kb_id = ?", (kb_id,))
        row = await cursor.fetchone()
        result["documents_deleted"] = row[0] if row else 0

        # 1. Delete chat sessions and messages for this kb_id
        try:
            # Delete messages for sessions linked to this kb_id
            await db.execute(
                "DELETE FROM messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE kb_id = ?)",
                (kb_id,),
            )
            await db.execute("DELETE FROM chat_sessions WHERE kb_id = ?", (kb_id,))
            logger.info("[KB] Chat history cleaned for kb=%s", kb_id)
        except Exception as exc:
            result["warnings"].append(f"Chat history cleanup failed: {exc}")
            logger.warning("[KB] Chat history cleanup failed kb=%s: %s", kb_id, exc)

        # 2-3. Delete document and KB records
        try:
            await db.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
            await db.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
            await db.commit()
            logger.info("[KB] DB records deleted kb=%s docs=%d", kb_id, result["documents_deleted"])
        except Exception as exc:
            result["success"] = False
            result["warnings"].append(f"DB delete failed: {exc}")
            logger.error("[KB] DB delete failed kb=%s: %s", kb_id, exc)

        # 4. Drop Milvus collection
        try:
            await milvus_client.drop_collection(kb_id)
            result["milvus_deleted"] = True
            logger.info("[KB] Milvus collection dropped kb=%s", kb_id)
        except Exception as exc:
            result["warnings"].append(f"Milvus collection drop failed: {exc}")
            logger.error("[KB] Milvus drop failed kb=%s: %s", kb_id, exc)

        # 5. Remove uploaded files
        kb_upload_dir = os.path.join(settings.UPLOAD_DIR, kb_id)
        if os.path.exists(kb_upload_dir):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, shutil.rmtree, kb_upload_dir)
                logger.info("[KB] Upload files removed kb=%s", kb_id)
            except Exception as exc:
                result["warnings"].append(f"Upload directory cleanup failed: {exc}")
                logger.warning("[KB] Upload directory cleanup failed kb=%s: %s", kb_id, exc)

        # 6. Remove BM25 index (always cleanup, even if hybrid search is disabled)
        try:
            from app.services.bm25_service import bm25_service
            await bm25_service.delete_index(kb_id)
            result["bm25_deleted"] = True
            logger.info("[KB] BM25 index deleted kb=%s", kb_id)
        except Exception as exc:
            result["warnings"].append(f"BM25 index delete failed: {exc}")
            logger.warning("[KB] BM25 index delete failed kb=%s: %s", kb_id, exc)

        logger.info(
            "[KB] Knowledge base deletion complete kb=%s success=%s docs=%d warnings=%d",
            kb_id, result["success"], result["documents_deleted"], len(result["warnings"]),
        )
        return result
