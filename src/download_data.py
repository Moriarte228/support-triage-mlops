"""Download BANKING77 to data/raw/banking77_{train,test}.csv.

Source: the original CSVs from github.com/PolyAI-LDN/task-specific-datasets (CC BY 4.0).
Columns are renamed to the project schema: text -> instruction, category -> intent.

Run from the project root:  python src/download_data.py
"""

from pathlib import Path

import pandas as pd

BASE_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        out = RAW_DIR / f"banking77_{split}.csv"
        if out.exists():
            print(f"Already exists: {out}")
            continue
        df = pd.read_csv(f"{BASE_URL}/{split}.csv")
        df = df.rename(columns={"text": "instruction", "category": "intent"})
        # Two labels have stray characters: "Refund_not_showing_up", "reverted_card_payment?"
        df["intent"] = df["intent"].str.lower().str.rstrip("?")
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} rows, {df['intent'].nunique()} intents -> {out}")


if __name__ == "__main__":
    main()