from fastapi import Request


def get_settings():
    from app.config import settings
    return settings


def get_milvus_client():
    from app.db.milvus_client import milvus_client
    return milvus_client


def get_db():
    from app.db.sqlite_database import get_database
    return get_database()


def get_embedding_service():
    from app.services.embedding_service import embedding_service
    return embedding_service


def get_llm_service():
    from app.services.llm_service import llm_service
    return llm_service


def get_document_service():
    from app.services.document_service import DocumentService
    from app.config import settings
    return DocumentService(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)


def get_ingestion_service():
    from app.services.ingestion_service import IngestionService
    return IngestionService()


def get_retrieval_service():
    from app.services.retrieval_service import RetrievalService
    return RetrievalService()


def get_rag_service():
    from app.services.rag_service import RAGService
    return RAGService()


def get_chat_history_service():
    from app.services.chat_history_service import ChatHistoryService
    return ChatHistoryService()
