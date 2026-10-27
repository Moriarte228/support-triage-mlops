"""Chunking strategies, selectable by name (e.g. from a config or an experiment loop)."""

from src.assistant.kb.chunking.base import Chunker, chunk_documents
from src.assistant.kb.chunking.heading import HeadingChunker

CHUNKERS = {
    HeadingChunker.name: HeadingChunker,
}


def get_chunker(name: str, **params) -> Chunker:
    """get_chunker("heading"); later e.g. get_chunker("window", size=200, overlap=50)."""
    if name not in CHUNKERS:
        raise ValueError(f"unknown chunker {name!r}, available: {sorted(CHUNKERS)}")
    return CHUNKERS[name](**params)


__all__ = ["CHUNKERS", "Chunker", "HeadingChunker", "chunk_documents", "get_chunker"]