import uuid
import json
from datetime import datetime
from app.db.sqlite_database import get_database
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class ChatHistoryService:
    async def create_session(self, kb_id: str | None, title: str = "New Chat") -> dict:
        session_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat()
        db = await get_database()
        await db.execute(
            "INSERT INTO chat_sessions (id, kb_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, kb_id, title, now, now),
        )
        await db.commit()
        return await self.get_session(session_id)

    async def get_session(self, session_id: str) -> dict | None:
        db = await get_database()
        cursor = await db.execute(
            """SELECT s.*,
               (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count
            FROM chat_sessions s WHERE s.id = ?""",
            (session_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_sessions(self, kb_id: str | None = None) -> list[dict]:
        db = await get_database()
        if kb_id:
            cursor = await db.execute(
                """SELECT s.*,
                   (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count
                FROM chat_sessions s WHERE s.kb_id = ? ORDER BY s.updated_at DESC""",
                (kb_id,),
            )
        else:
            cursor = await db.execute(
                """SELECT s.*,
                   (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count
                FROM chat_sessions s ORDER BY s.updated_at DESC"""
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def delete_session(self, session_id: str) -> None:
        db = await get_database()
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await db.commit()

    async def add_message(self, session_id: str, role: str, content: str, sources: list[dict] | None = None) -> str:
        msg_id = uuid.uuid4().hex[:12]
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        now = datetime.utcnow().isoformat()
        db = await get_database()
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, role, content, sources_json, now),
        )
        await db.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        await db.commit()
        return msg_id

    async def get_history(self, session_id: str, limit: int = 10) -> list[dict]:
        db = await get_database()
        cursor = await db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit * 2),
        )
        rows = await cursor.fetchall()
        messages = [dict(row) for row in rows]
        messages.reverse()
        return messages

    async def get_messages(self, session_id: str) -> list[dict]:
        db = await get_database()
        cursor = await db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    def format_history_for_llm(self, history: list[dict]) -> list:
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages
