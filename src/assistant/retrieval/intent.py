"""Retrieve sections through the intent classifier (the router).

The classifier gives a probability for each of the 77 intents. Every section is
tagged with the intents it answers, so the probability that a section is the
right one is the sum of the probabilities of its intents:

    P("When will my card arrive?") = P(card_arrival) + P(card_delivery_estimate)

Two close intents that lead to the same section are therefore not ambiguous.
"""

from collections import defaultdict
from pathlib import Path

import joblib

from src.assistant.kb.schema import Chunk
from src.assistant.retrieval.base import Hit, matches_filters
from src.preprocess import normalize

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROUTER = ROOT / "models" / "router.joblib"


class IntentRetriever:
    name = "intent"

    def __init__(self, chunks: list[Chunk], router=None, router_path: Path | str = DEFAULT_ROUTER):
        # `router` can be passed directly (e.g. a fake model in tests); otherwise it is loaded from disk.
        self.router = router if router is not None else joblib.load(router_path)
        self.intents = list(self.router.classes_)

        self.chunks_by_intent: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            for intent in chunk.metadata.get("intents", []):
                self.chunks_by_intent[intent].append(chunk)

        missing = [intent for intent in self.intents if intent not in self.chunks_by_intent]
        if missing:
            raise ValueError(f"no knowledge-base section for intents: {missing}")

    def retrieve(self, query: str, k: int = 3, filters: dict | None = None) -> list[Hit]:
        # The router was trained on normalize()d text, so serving must apply the same transform.
        proba = self.router.predict_proba([normalize(query)])[0]

        scores: dict[str, float] = defaultdict(float)
        contributions: dict[str, dict[str, float]] = defaultdict(dict)
        chunk_by_id: dict[str, Chunk] = {}
        for intent, p in zip(self.intents, proba):
            for chunk in self.chunks_by_intent[intent]:
                if not matches_filters(chunk, filters):
                    continue
                scores[chunk.id] += float(p)
                contributions[chunk.id][intent] = round(float(p), 4)
                chunk_by_id[chunk.id] = chunk

        top = sorted(scores, key=scores.get, reverse=True)[:k]
        return [
            Hit(
                chunk=chunk_by_id[chunk_id],
                score=scores[chunk_id],
                source=self.name,
                details={"intents": dict(sorted(contributions[chunk_id].items(), key=lambda kv: -kv[1]))},
            )
            for chunk_id in top
        ]