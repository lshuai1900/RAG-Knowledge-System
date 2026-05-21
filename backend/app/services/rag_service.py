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

    @staticmethod
    def _build_section_annotation(hit: dict) -> str:
        """Build a section annotation string from hit metadata."""
        parts = []
        sp = hit.get("section_path")
        if sp:
            parts.append(sp)
        elif hit.get("section_title"):
            parts.append(hit["section_title"])
        page = hit.get("page")
        if page is not None:
            parts.append(f"第{page + 1}页")  # PyPDFLoader pages are 0-indexed
        if parts:
            return f" ({' | '.join(parts)})"
        return ""

    @staticmethod
    def _build_source(hit: dict) -> dict:
        source = {
            "content": hit["content"][:300],
            "document_name": hit["document_name"],
            "chunk_index": hit["chunk_index"],
            "score": round(hit["score"], 4),
        }
        if hit.get("section_title"):
            source["section_title"] = hit["section_title"]
        if hit.get("section_path"):
            source["section_path"] = hit["section_path"]
        if hit.get("page") is not None:
            source["page"] = hit["page"]
        return source

    async def query_stream(self, kb_id: str, session_id: str, query: str) -> AsyncIterator[dict]:
        history = await self.history_service.get_history(session_id, self.max_history_turns * 2)

        await self.history_service.add_message(session_id, "user", query)
        results = await self.retrieval.search(kb_id, query)

        context_parts = []
        sources = []
        for hit in results:
            section_annotation = self._build_section_annotation(hit)
            context_parts.append(
                f"[Source: {hit['document_name']}{section_annotation}]\n{hit['content']}"
            )
            sources.append(self._build_source(hit))

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
            section_annotation = self._build_section_annotation(hit)
            context_parts.append(
                f"[Source: {hit['document_name']}{section_annotation}]\n{hit['content']}"
            )
            sources.append(self._build_source(hit))

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
        system_prompt = SYSTEM_TEMPLATE.format(context=context)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(self.history_service.format_history_for_llm(history))
        messages.append(HumanMessage(content=query))

        answer = await llm_service.generate(messages)
        msg_id = await self.history_service.add_message(session_id, "assistant", answer, sources)
        return {"answer": answer, "sources": sources, "message_id": msg_id}
