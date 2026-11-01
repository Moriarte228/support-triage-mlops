"""Tests for the batch data contract (no database or MLflow needed)."""

from pathlib import Path

import pandas as pd
import pytest

from src.training import data
from src.training.data import INITIAL, BatchError, validate_batch

ROOT = Path(__file__).resolve().parents[1]
needs_data = pytest.mark.skipif(
    not (ROOT / "data" / "processed" / "val.csv").exists(), reason="run python -m src.prepare_data first"
)
KNOWN = {"card_arrival", "terminate_account"}


@pytest.fixture(autouse=True)
def no_holdout(monkeypatch):
    """By default pretend val/test are empty; the leakage test sets them explicitly."""
    monkeypatch.setattr(data, "holdout_keys", lambda: frozenset())


def batch(rows):
    return pd.DataFrame(rows, columns=["instruction", "intent"])


def test_clean_batch_passes_with_a_report():
    rows = [("where is my card", "card_arrival"), ("close it", "terminate_account")]
    clean, report = validate_batch(batch(rows), KNOWN)
    assert len(clean) == 2
    assert report == {"rows": 2, "kept": 2, "empty_text": 0, "unknown_intent": 0, "duplicate": 0}


def test_text_is_normalised_like_in_training():
    clean, _ = validate_batch(batch([("card 1234 not here", "card_arrival")]), KNOWN)
    assert clean.loc[0, "text"] == "card <num> not here"


def test_missing_column_is_rejected():
    with pytest.raises(BatchError, match="missing columns"):
        validate_batch(pd.DataFrame({"instruction": ["x"]}), KNOWN)


def test_a_few_bad_rows_are_dropped():
    rows = [(f"query number {chr(97 + i)}", "card_arrival") for i in range(25)] + [("odd one", "new_intent")]
    clean, report = validate_batch(batch(rows), KNOWN)  # 1 bad row out of 26 is under the 5% limit
    assert report["unknown_intent"] == 1
    assert len(clean) == 25


def test_too_many_bad_rows_reject_the_batch():
    rows = [("a", "card_arrival"), ("b", "unknown"), ("c", "unknown")]
    with pytest.raises(BatchError, match="too many bad rows"):
        validate_batch(batch(rows), KNOWN)


@needs_data
def test_rows_from_val_or_test_are_never_loaded(monkeypatch):
    monkeypatch.undo()  # use the real holdout_keys
    data.holdout_keys.cache_clear()
    val_row = pd.read_csv(ROOT / "data" / "processed" / "val.csv").iloc[0]
    with pytest.raises(BatchError, match="overlap with val/test"):
        validate_batch(batch([(val_row["instruction"], val_row["intent"])]), {val_row["intent"]})


def test_initial_training_set_comes_first():
    assert data.all_batch_ids()[0] == INITIAL
