"""Tests for IntentRetriever.

Unit tests use a fake router with fixed probabilities, so the expected result
can be computed by hand. One integration test runs the real model, if it exists.
"""

from pathlib import Path

import numpy as np
import pytest

from src.assistant.kb.schema import Chunk
from src.assistant.retrieval import IntentRetriever

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "models" / "router.joblib"
INDEX = ROOT / "data" / "index" / "heading" / "chunks.jsonl"

PROBA = {
    "card_arrival": 0.3,
    "card_delivery_estimate": 0.2,
    "terminate_account": 0.4,
    "cancel_transfer": 0.1,
}


class FakeRouter:
    """Stands in for the sklearn model: fixed probabilities, no training."""

    def __init__(self, proba: dict[str, float]):
        self.classes_ = np.array(sorted(proba))  # sklearn keeps classes sorted
        self._row = np.array([[proba[c] for c in self.classes_]])
        self.seen: list[str] = []  # texts the retriever passed in

    def predict_proba(self, texts):
        self.seen.extend(texts)
        return np.repeat(self._row, len(texts), axis=0)  # one row per text


def make_chunk(chunk_id: str, intents: list[str]) -> Chunk:
    doc_id = chunk_id.split("#")[0]
    return Chunk(
        id=chunk_id,
        doc_id=doc_id,
        text=f"text of {chunk_id}",
        metadata={"intents": intents},
    )


@pytest.fixture
def chunks():
    return [
        make_chunk("cards#arrival", ["card_arrival", "card_delivery_estimate"]),
        make_chunk("account#close", ["terminate_account"]),
        make_chunk("transfers#cancel", ["cancel_transfer"]),
    ]


@pytest.fixture
def router():
    return FakeRouter(PROBA)


@pytest.fixture
def retriever(chunks, router):
    return IntentRetriever(chunks, router=router)


def test_section_score_is_sum_of_its_intents(retriever):
    hits = retriever.retrieve("anything", k=3)
    assert hits[0].chunk.id == "cards#arrival"
    assert hits[0].score == pytest.approx(0.3 + 0.2)
