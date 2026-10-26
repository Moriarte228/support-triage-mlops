"""Build the train / val / test splits and the daily batches for the ETL simulation.

Run once from the project root:  python -m src.prepare_data

Layout:
  test  15%  fixed hold-out, used only for the final model
  val   15%  model selection
  train 70%  INITIAL_SHARE of it trains the first model,
             the rest is cut into N_BATCHES "daily" batches that Airflow ingests later
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.preprocess import SEED, TARGET, deduplicate, split

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bitext.csv"
PROCESSED = ROOT / "data" / "processed"
BATCHES = ROOT / "data" / "batches"

INITIAL_SHARE = 0.4
N_BATCHES = 10


def main() -> None:
    df = deduplicate(pd.read_csv(RAW))
    train, val, test = split(df)

    initial = train.groupby(TARGET, group_keys=False).sample(frac=INITIAL_SHARE, random_state=SEED)
    stream = train.drop(initial.index).sample(frac=1.0, random_state=SEED)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    BATCHES.mkdir(parents=True, exist_ok=True)
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