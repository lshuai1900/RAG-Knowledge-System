import os
import asyncio
import logging
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import settings
from app.services.semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


class DocumentService:
    LOADER_MAP = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".md": TextLoader,
        ".docx": Docx2txtLoader,
        ".doc": Docx2txtLoader,
    }

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Keep recursive splitter as fallback
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
        )

    async def load_and_chunk(
        self, file_path: str, file_extension: str,
        doc_id: str = "", filename: str = "",
    ) -> list[Document]:
        loader_cls = self.LOADER_MAP.get(file_extension.lower())
        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {file_extension}")

        loop = asyncio.get_event_loop()
        loader = loader_cls(file_path)

        def _load():
            documents = loader.load()
            for doc in documents:
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["source"] = os.path.basename(file_path)
            return documents

        raw_docs = await loop.run_in_executor(None, _load)

        strategy = settings.CHUNK_STRATEGY

        if strategy == "semantic":
            try:
                return await self._semantic_chunk(raw_docs, doc_id, filename)
            except Exception as e:
                logger.warning(
                    "[DocumentService] Semantic chunking failed for '%s': %s. Falling back to recursive.",
                    filename, e,
                )
                return await self._recursive_chunk(raw_docs)
        else:
            return await self._recursive_chunk(raw_docs)

    async def _semantic_chunk(
        self, raw_docs: list[Document], doc_id: str, filename: str,
    ) -> list[Document]:
        chunker = SemanticChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=settings.MIN_CHUNK_SIZE,
            max_chunk_size=settings.MAX_CHUNK_SIZE,
            doc_id=doc_id,
            document_name=filename,
        )

        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(None, chunker.split_documents, raw_docs)

        # Carry over page info from loader metadata for PyPDFLoader pages
        # Build a lookup of approximate page from original documents
        self._attach_page_info(chunks, raw_docs)

        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            if not chunk.metadata.get("chunk_id"):
                chunk.metadata["chunk_id"] = f"{doc_id}_{i}"

        return chunks

    def _attach_page_info(
        self, chunks: list[Document], raw_docs: list[Document],
    ) -> None:
        """Attach page info to chunks by substring matching against source pages."""
        # Build list of (page, text) from source documents
        page_texts = []
        for doc in raw_docs:
            page_num = doc.metadata.get("page")
            if page_num is not None:
                page_texts.append((page_num, doc.page_content))

        if not page_texts:
            return

        for chunk in chunks:
            if chunk.metadata.get("page") is not None:
                continue
            content = chunk.page_content[:60]  # match by first 60 chars
            for page_num, page_text in page_texts:
                if content and content in page_text:
                    chunk.metadata["page"] = page_num
                    break

    async def _recursive_chunk(self, raw_docs: list[Document]) -> list[Document]:
        loop = asyncio.get_event_loop()

        def _split():
            chunks = self._recursive_splitter.split_documents(raw_docs)
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
            return chunks

        return await loop.run_in_executor(None, _split)
