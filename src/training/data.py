"""Labelled batches: find the next one, check it, load it into Postgres, read the training set back.

New labelled requests arrive as data/batches/batch_XX.csv (made by src.prepare_data).
The first training set, data/processed/train.csv, is loaded as the batch "initial".
"""

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.preprocess import TARGET, TEXT, dedup_key, normalize

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
INITIAL = "initial"
MAX_DROPPED_SHARE = 0.05  # more bad rows than this means a broken batch, not noise


class BatchError(ValueError):
    """The batch breaks the data contract and must not be loaded."""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.getenv("TRAINING_DATABASE_URL")
    if not url:
        raise RuntimeError("TRAINING_DATABASE_URL is not set")
    return create_engine(url, pool_pre_ping=True)


# ---- files ----

def batch_path(batch_id: str) -> Path:
    if batch_id == INITIAL:
        return DATA / "processed" / "train.csv"
    return DATA / "batches" / f"{batch_id}.csv"


def all_batch_ids() -> list[str]:
    return [INITIAL] + sorted(path.stem for path in (DATA / "batches").glob("batch_*.csv"))


def read_batch(batch_id: str) -> pd.DataFrame:
    return pd.read_csv(batch_path(batch_id))


def read_val() -> pd.DataFrame:
    return pd.read_csv(DATA / "processed" / "val.csv")


@lru_cache(maxsize=1)
def holdout_keys() -> frozenset[str]:
    """Texts of val and test: they must never get into training."""
    frames = [pd.read_csv(DATA / "processed" / f"{name}.csv") for name in ("val", "test")]
    texts = pd.concat(frames)[TEXT].astype(str)
    return frozenset(texts.map(normalize).map(dedup_key))


# ---- the data contract ----

def validate_batch(df: pd.DataFrame, known_intents: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Return the clean rows and a report; raise BatchError if the batch is broken."""
    missing = {TEXT, TARGET} - set(df.columns)
    if missing:
        raise BatchError(f"missing columns: {sorted(missing)}")

    known_intents = known_intents if known_intents is not None else set(read_val()[TARGET])
    df = df.assign(text=df[TEXT].astype(str).map(normalize))
    key = df["text"].map(dedup_key)

    leaked = key.isin(holdout_keys())
    if leaked.any():
        raise BatchError(f"{int(leaked.sum())} rows overlap with val/test: evaluation would be invalid")

    checks = {
        "empty_text": df["text"].str.strip() == "",
        "unknown_intent": ~df[TARGET].isin(known_intents),
        "duplicate": key.duplicated(),
    }
    bad = pd.concat(checks, axis=1).any(axis=1)
    report = {"rows": len(df), "kept": int((~bad).sum()), **{name: int(mask.sum()) for name, mask in checks.items()}}
    if len(df) == 0 or bad.mean() > MAX_DROPPED_SHARE:
        raise BatchError(f"too many bad rows: {report}")
    return df.loc[~bad, ["text", TARGET]].reset_index(drop=True), report


# ---- Postgres ----

def loaded_batch_ids(engine: Engine | None = None) -> set[str]:
    with (engine or get_engine()).connect() as conn:
        return set(conn.execute(text("SELECT DISTINCT batch_id FROM training.labeled_requests")).scalars())


def loaded_in_order(engine: Engine | None = None) -> list[str]:
    """Loaded batches in arrival order: initial, batch_01, batch_02, ..."""
    loaded = loaded_batch_ids(engine)
    return [batch_id for batch_id in all_batch_ids() if batch_id in loaded]


def next_batch_id(engine: Engine | None = None) -> str | None:
    loaded = loaded_batch_ids(engine)
    return next((batch_id for batch_id in all_batch_ids() if batch_id not in loaded), None)


def load_batch(batch_id: str, clean: pd.DataFrame, engine: Engine | None = None) -> int:
    """Replace the rows of this batch in one transaction: running it twice never duplicates data."""
    rows = [{"batch_id": batch_id, "text": t, "intent": i} for t, i in zip(clean["text"], clean[TARGET])]
    with (engine or get_engine()).begin() as conn:
        conn.execute(text("DELETE FROM training.labeled_requests WHERE batch_id = :b"), {"b": batch_id})
        conn.execute(
            text("INSERT INTO training.labeled_requests (batch_id, text, intent) VALUES (:batch_id, :text, :intent)"),
            rows,
        )
    return len(rows)


def load_training_set(engine: Engine | None = None) -> pd.DataFrame:
    with (engine or get_engine()).connect() as conn:
        result = conn.execute(text("SELECT text, intent FROM training.labeled_requests ORDER BY id"))
        return pd.DataFrame(result.fetchall(), columns=["text", TARGET])
