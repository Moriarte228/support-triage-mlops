"""Text normalisation, de-duplication and splitting.

normalize() is shared by training and serving: the API must apply exactly the same transform.
"""

from __future__ import annotations

import re

import pandas as pd
from sklearn.model_selection import train_test_split

TEXT, TARGET = "instruction", "intent"
SEED = 42

_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s<>]")


def normalize(text: str) -> str:
    """Map literal numbers (amounts, card digits, dates) to <num>, collapse whitespace."""
    text = _DIGITS.sub(" <num> ", text)
    return _SPACES.sub(" ", text).strip()


def dedup_key(text: str) -> str:
    """Comparison key: case, punctuation and spacing differences do not make a text unique."""
    return _SPACES.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Add a normalised `text` column, drop texts with conflicting labels, then duplicates."""
    df = df.assign(text=df[TEXT].astype(str).map(normalize))
    key = df["text"].map(dedup_key)
    n_intents = df.groupby(key)[TARGET].transform("nunique")
    n_conflicts = int((n_intents > 1).sum())
    keep = n_intents == 1
    df, key = df[keep], key[keep]
    n_before = len(df)
    df = df[~key.duplicated()]
    print(
        f"Dropped {n_conflicts} rows with conflicting labels and "
        f"{n_before - len(df)} duplicates; {len(df)} rows left"
    )
    return df.reset_index(drop=True)


def drop_overlap(df: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    """Drop rows of `df` whose text also appears in `other` (e.g. train rows that are in test)."""
    other_keys = set(other["text"].map(dedup_key))
    overlap = df["text"].map(dedup_key).isin(other_keys)
    print(f"Dropped {int(overlap.sum())} rows that also appear in the other set")
    return df[~overlap].reset_index(drop=True)


def train_val_split(
    df: pd.DataFrame, val_size: float = 0.15, seed: int = SEED
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified train / validation split on the intent."""
    train, val = train_test_split(df, test_size=val_size, stratify=df[TARGET], random_state=seed)
    return train.reset_index(drop=True), val.reset_index(drop=True)

# Verified manually in notebooks/01_eda.ipynb: matches only support-agent replies
# (5 rows in BANKING77 train, all labelled unable_to_verify_identity; none in test).
AGENT_REPLY_PATTERN = r"\b(?:from us|you will hear|we will|we'll)\b"


def drop_agent_replies(df: pd.DataFrame, text_col: str = "instruction") -> pd.DataFrame:
    """Remove texts written from the bank's side: they are not customer queries."""
    mask = df[text_col].str.contains(AGENT_REPLY_PATTERN, case=False, regex=True)
    print(f"drop_agent_replies: removed {mask.sum()} rows")
    return df.loc[~mask].reset_index(drop=True)