"""Download the Bitext customer-support dataset to data/raw/bitext.csv.
 
Run from the project root:  python src/download_data.py
"""
 
from pathlib import Path
 
from datasets import load_dataset
 
DATASET = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
ROOT = Path(__file__).resolve().parents[1]  # src/ -> project root
OUT = ROOT / "data" / "raw" / "bitext.csv"
 
 
def main() -> None:
    if OUT.exists():
        print(f"Already exists: {OUT}")
        return
    df = load_dataset(DATASET, split="train").to_pandas()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} rows, columns: {list(df.columns)} -> {OUT}")
 
 
if __name__ == "__main__":
    main()
