"""Tests for loading and chunking the knowledge base.

They check properties that must hold for any size of the knowledge base,
not exact counts: adding an article must not break them.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.assistant.kb.chunking import chunk_documents, get_chunker
from src.assistant.kb.loaders import load_markdown

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "kb"
TRAIN = ROOT / "data" / "processed" / "train.csv"


@pytest.fixture(scope="module")
def docs():
    return load_markdown(KB_DIR)


@pytest.fixture(scope="module")
def chunks(docs):
    return chunk_documents(docs, get_chunker("heading"))


def test_every_article_file_is_loaded(docs):
    article_files = [
        path for path in KB_DIR.glob("*.md") if path.name.lower() != "readme.md"
    ]
    assert len(docs) == len(article_files)


def test_every_document_has_chunks(docs, chunks):
    docs_with_chunks = {chunk.doc_id for chunk in chunks}
    empty = [doc.id for doc in docs if doc.id not in docs_with_chunks]
    assert not empty, f"documents without chunks: {empty}"


def test_chunk_ids_are_unique(chunks):
    ids = [chunk.id for chunk in chunks]
    duplicates = sorted({chunk_id for chunk_id in ids if ids.count(chunk_id) > 1})
    assert not duplicates, f"duplicate chunk ids: {duplicates}"


def test_chunk_text_is_clean(chunks):
    empty = [chunk.id for chunk in chunks if not chunk.text.split("\n", 1)[-1].strip()]
    with_labels = [chunk.id for chunk in chunks if "<!--" in chunk.text]
    assert not empty, f"chunks with an empty body: {empty}"
    assert not with_labels, f"chunks with leftover labels: {with_labels}"


def test_every_chunk_has_intents(chunks):
    i = 0
    for chunk in chunks:
        intents = chunk.metadata.get("intents", [])
        if len(intents) == 0:
            i += 1
    assert i == 0, f"Chunks that doesn't have intents: {i}"


@pytest.mark.skipif(
    not TRAIN.exists(), reason="no training data: run python -m src.prepare_data"
)
def test_all_train_intents_covered(chunks):
    train_intents = set(pd.read_csv(TRAIN)["intent"])
    covered = {intent for chunk in chunks for intent in chunk.metadata["intents"]}
    missing = sorted(train_intents - covered)
    assert not missing, f"intents without a section: {missing}"
