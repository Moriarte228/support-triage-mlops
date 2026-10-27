"""Retrievers, selectable by name. Every retriever takes the chunks as its first argument."""

from src.assistant.kb.schema import Chunk
from src.assistant.retrieval.base import Hit, Retriever, matches_filters
from src.assistant.retrieval.intent import IntentRetriever

RETRIEVERS = {
    IntentRetriever.name: IntentRetriever,
}


def get_retriever(name: str, chunks: list[Chunk], **params) -> Retriever:
    """get_retriever("intent", chunks); later e.g. get_retriever("bm25", chunks)."""
    if name not in RETRIEVERS:
        raise ValueError(f"unknown retriever {name!r}, available: {sorted(RETRIEVERS)}")
    return RETRIEVERS[name](chunks, **params)


__all__ = ["RETRIEVERS", "Hit", "IntentRetriever", "Retriever", "get_retriever", "matches_filters"]