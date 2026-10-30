"""Tests for IntentRetriever.

Unit tests use a fake router with fixed probabilities, so the expected result
can be computed by hand. One integration test runs the real model, if it exists.
"""

from pathlib import Path

import numpy as np
import pytest

from src.assistant.kb.schema import Chunk
from src.assistant.retrieval import IntentRetriever
from src.assistant.kb.store import load_chunks

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
        self.classes_ = np.array(sorted(proba))            # sklearn keeps classes sorted
        self._row = np.array([[proba[c] for c in self.classes_]])
        self.seen: list[str] = []                          # texts the retriever passed in

    def predict_proba(self, texts):
        self.seen.extend(texts)
        return np.repeat(self._row, len(texts), axis=0)    # one row per text


def make_chunk(chunk_id: str, intents: list[str]) -> Chunk:
    doc_id = chunk_id.split("#")[0]
    return Chunk(id=chunk_id, doc_id=doc_id, text=f"text of {chunk_id}", metadata={"intents": intents})


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

def test_hits_sorted_by_score(retriever):
    hits = retriever.retrieve("anything", k=10)
    ok = True
    for i in range(1, len(hits)):
        if hits[i].score > hits[i - 1].score:
            ok = False
            break
    assert ok, f"Some of scores not in descending order"

def test_k_limits_number_of_hits(retriever, chunks):
    small_k, big_k = 1, 10
    hits_a = retriever.retrieve("anything", k=small_k)
    assert len(hits_a) == small_k, f"expected {small_k} hits, got {len(hits_a)}"
    hits_b = retriever.retrieve("anything", k=big_k)
    assert len(hits_b) == len(chunks), f"expected {len(chunks)} hits (all chunks), got {len(hits_b)}"

def test_details_show_contributions(retriever):
    details = retriever.retrieve("anything", k=1)[0].details["intents"]
    assert details == {"card_arrival": PROBA["card_arrival"], "card_delivery_estimate": PROBA["card_delivery_estimate"]}
    assert list(details) == ["card_arrival", "card_delivery_estimate"]  # bigger contribution first


def test_filters_restrict_sections(retriever):
    hits = retriever.retrieve("anything", k=3, filters={"doc_id": "account"})
    assert [hit.chunk.id for hit in hits] == ["account#close"]

def test_query_is_normalized(retriever):
    query = "I was charged 5 euros"
    _ = retriever.retrieve(query)
    assert retriever.router.seen == ["I was charged <num> euros"]

def test_router_intent_without_section_raises(chunks):
    router_with_unknown_intent = FakeRouter({**PROBA, 
                                             "unknown_intent": 0.0})
    with pytest.raises(ValueError, match="unknown_intent"):
        retriever = IntentRetriever(chunks, router=router_with_unknown_intent)

@pytest.mark.skipif(not ROUTER.exists() or not INDEX.exists(), reason="no chunks or no router exists")
def test_real_router_close_account():
    chunks = load_chunks(INDEX)
    retriever = IntentRetriever(chunks)  # no router passed: loads models/router.joblib
    hits = retriever.retrieve("I want to close my account", k=1)
    assert hits[0].chunk.id == "account#closing-my-account"


