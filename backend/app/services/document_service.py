import os
import asyncio
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentService:
    LOADER_MAP = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".md": TextLoader,
        ".docx": Docx2txtLoader,
        ".doc": Docx2txtLoader,
    }

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def load_and_chunk(self, file_path: str, file_extension: str) -> list[Document]:
        loader_cls = self.LOADER_MAP.get(file_extension.lower())
        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {file_extension}")

        loop = asyncio.get_event_loop()
        loader = loader_cls(file_path)

        def _load_and_split():
            documents = loader.load()
            for doc in documents:
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["source"] = os.path.basename(file_path)
            chunks = self.text_splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
            return chunks

        return await loop.run_in_executor(None, _load_and_split)
