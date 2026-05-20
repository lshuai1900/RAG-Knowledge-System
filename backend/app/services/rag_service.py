from typing import AsyncIterator
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import llm_service
from app.services.chat_history_service import ChatHistoryService

SYSTEM_TEMPLATE = """You are a helpful assistant answering questions based on provided context and conversation history.

Core rules:
1. Use the context below as your primary reference for factual questions.
2. If the context doesn't contain the answer, use conversation history to answer follow-up questions (e.g. user asks "what's my name?" after telling you earlier).
3. If neither context nor history has the answer, say so clearly.
4. When referencing information from context, cite the source document name.

=== CONTEXT ===
{context}"""


class RAGService:
    def __init__(self):
        self.retrieval = RetrievalService()
        self.history_service = ChatHistoryService()
        self.max_history_turns = settings.MAX_HISTORY_TURNS

    async def query_stream(self, kb_id: str, session_id: str, query: str) -> AsyncIterator[dict]:
        history = await self.history_service.get_history(session_id, self.max_history_turns * 2)

        await self.history_service.add_message(session_id, "user", query)
        results = await self.retrieval.search(kb_id, query)

        context_parts = []
        sources = []
        for hit in results:
            context_parts.append(f"[Source: {hit['document_name']}]\n{hit['content']}")
            sources.append({
                "content": hit["content"][:300],
                "document_name": hit["document_name"],
                "chunk_index": hit["chunk_index"],
                "score": round(hit["score"], 4),
            })

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
        system_prompt = SYSTEM_TEMPLATE.format(context=context)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(self.history_service.format_history_for_llm(history))
        messages.append(HumanMessage(content=query))

        full_answer = ""
        async for token in llm_service.stream(messages):
            if token:
                full_answer += token
                yield {"type": "chunk", "text": token}

        msg_id = await self.history_service.add_message(session_id, "assistant", full_answer, sources)
        yield {"type": "sources", "sources": sources}
        yield {"type": "done", "message_id": msg_id}

    async def query(self, kb_id: str, session_id: str, query: str) -> dict:
        history = await self.history_service.get_history(session_id, self.max_history_turns * 2)
        await self.history_service.add_message(session_id, "user", query)
        results = await self.retrieval.search(kb_id, query)

        context_parts = []
        sources = []
        for hit in results:
            context_parts.append(f"[Source: {hit['document_name']}]\n{hit['content']}")
            sources.append({
                "content": hit["content"][:300],
                "document_name": hit["document_name"],
                "chunk_index": hit["chunk_index"],
                "score": round(hit["score"], 4),
            })

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
        system_prompt = SYSTEM_TEMPLATE.format(context=context)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(self.history_service.format_history_for_llm(history))
        messages.append(HumanMessage(content=query))

        answer = await llm_service.generate(messages)
        msg_id = await self.history_service.add_message(session_id, "assistant", answer, sources)
        return {"answer": answer, "sources": sources, "message_id": msg_id}
