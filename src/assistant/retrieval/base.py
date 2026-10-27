"""Common interface for retrievers."""

from dataclasses import dataclass, field
from typing import Protocol

from src.assistant.kb.schema import Chunk


@dataclass
class Hit:
    chunk: Chunk
    score: float   # higher is better; scales differ between retrievers
    source: str    # which retriever found it: "intent", "bm25", "dense", "rerank"
    details: dict = field(default_factory=dict)  # retriever-specific info for logs


class Retriever(Protocol):
    name: str

    def retrieve(self, query: str, k: int = 3, filters: dict | None = None) -> list[Hit]: ...


def matches_filters(chunk: Chunk, filters: dict | None) -> bool:
    """True if every filter key equals the chunk's metadata value, e.g. {"doc_id": "account"}."""
    if not filters:
        return True
    return all(chunk.metadata.get(key, getattr(chunk, key, None)) == value for key, value in filters.items())