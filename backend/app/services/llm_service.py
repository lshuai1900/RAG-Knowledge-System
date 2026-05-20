from typing import AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.config import settings


class LLMService:
    def __init__(self):
        self._llm: ChatOpenAI | None = None

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_BASE,
                model=settings.DEEPSEEK_MODEL_NAME,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                streaming=True,
            )
        return self._llm

    async def generate(self, messages: list[BaseMessage]) -> str:
        response = await self._get_llm().ainvoke(messages)
        return response.content

    async def stream(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        async for chunk in self._get_llm().astream(messages):
            if chunk.content:
                yield chunk.content


llm_service = LLMService()
