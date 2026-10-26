"""Build train / val / test and the daily ETL batches from BANKING77.

Run once from the project root:  python -m src.prepare_data

Layout:
  test        the official BANKING77 test set (3,080 rows, 40 per intent; 3,075 after
              deduplication), used only at the end
  val         VAL_SIZE of the official train set, stratified, for model selection
  train pool  the rest of the official train set:
                INITIAL_SHARE of it trains model v1,
                the rest is cut into N_BATCHES "daily" batches that Airflow ingests later.
              After all batches are ingested the model sees the full train set,
              which makes it comparable with published BANKING77 results.

Cleaning of the official train set (the test set is only deduplicated):
  - support-agent replies are removed: 5 texts written from the bank's side,
    all labelled unable_to_verify_identity (see notebooks/01_eda.ipynb);
  - duplicates are removed (case- and punctuation-insensitive);
  - rows that also appear in test are removed.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.preprocess import (
    SEED,
    TARGET,
    deduplicate,
    drop_agent_replies,
    drop_overlap,
    train_val_split,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
BATCHES = ROOT / "data" / "batches"

VAL_SIZE = 0.15
INITIAL_SHARE = 0.4
N_BATCHES = 10


def main() -> None:
    print("test:")
    test = deduplicate(pd.read_csv(RAW / "banking77_test.csv"))
    print("train:")
    train_raw = drop_agent_replies(pd.read_csv(RAW / "banking77_train.csv"))
    train_all = drop_overlap(deduplicate(train_raw), test)

    pool, val = train_val_split(train_all, val_size=VAL_SIZE)
    initial = pool.groupby(TARGET, group_keys=False).sample(frac=INITIAL_SHARE, random_state=SEED)
    stream = pool.drop(initial.index).sample(frac=1.0, random_state=SEED)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    BATCHES.mkdir(parents=True, exist_ok=True)
    for old in BATCHES.glob("batch_*.csv"):
        old.unlink()
    for name, part in {"train": initial, "val": val, "test": test}.items():
        part.to_csv(PROCESSED / f"{name}.csv", index=False)

    size = math.ceil(len(stream) / N_BATCHES)
    for i in range(N_BATCHES):
        stream.iloc[i * size : (i + 1) * size].to_csv(
            BATCHES / f"batch_{i + 1:02d}.csv", index=False
        )

    print(
        f"train={len(initial)} val={len(val)} test={len(test)} | "
        f"{len(stream)} rows in {N_BATCHES} batches -> {BATCHES}"
    )


if __name__ == "__main__":
    main()