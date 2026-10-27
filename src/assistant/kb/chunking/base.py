"""Common interface for chunking strategies."""

from typing import Protocol

from src.assistant.kb.schema import Chunk, Document


class Chunker(Protocol):
    name: str  # logged to MLflow to tell experiments apart

    def split(self, doc: Document) -> list[Chunk]: ...


def chunk_documents(docs: list[Document], chunker: Chunker) -> list[Chunk]:
    """Chunk all documents with the given strategy and check that chunk ids are unique."""
    chunks = [chunk for doc in docs for chunk in chunker.split(doc)]

    ids = [chunk.id for chunk in chunks]
    duplicates = {chunk_id for chunk_id in ids if ids.count(chunk_id) > 1}
    if duplicates:
        raise ValueError(f"duplicate chunk ids: {sorted(duplicates)}")
    return chunks