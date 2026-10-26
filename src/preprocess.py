"""Text normalisation, de-duplication and splitting.

normalize() is shared by training and serving: the API must apply exactly the same transform.
"""

from __future__ import annotations

import re

import pandas as pd
from sklearn.model_selection import train_test_split

TEXT, TARGET, CATEGORY = "instruction", "intent", "category"
SEED = 42

_NUMERIC_PH = re.compile(r"\{\{(?:Order Number|Invoice Number|Refund Amount)\}\}")
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s<>{}]")


def normalize(text: str) -> str:
    """Map numeric placeholders and literal numbers to <num>, collapse whitespace."""
    text = _NUMERIC_PH.sub(" <num> ", text)
    text = _DIGITS.sub(" <num> ", text)
    return _SPACES.sub(" ", text).strip()


def dedup_key(text: str) -> str:
    """Comparison key: case, punctuation and spacing differences do not make a text unique."""
    return _SPACES.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Add a normalised `text` column, drop texts with conflicting labels, then duplicates.

    Done before splitting, so identical texts cannot end up in both train and test.
    """
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


def split(
    df: pd.DataFrame, test_size: float = 0.15, val_size: float = 0.15, seed: int = SEED
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train / val / test split on the intent."""
    rest, test = train_test_split(df, test_size=test_size, stratify=df[TARGET], random_state=seed)
    train, val = train_test_split(
        rest, test_size=val_size / (1 - test_size), stratify=rest[TARGET], random_state=seed
    )
    return train, val, test