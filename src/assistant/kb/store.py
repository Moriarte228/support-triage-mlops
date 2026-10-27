"""Save and load chunks as JSON Lines: one chunk per line, easy to read and diff."""

import json
from dataclasses import asdict
from pathlib import Path

from src.assistant.kb.schema import Chunk


def save_chunks(chunks: list[Chunk], path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def load_chunks(path: Path | str) -> list[Chunk]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run  python -m src.assistant.kb.build")
    with path.open(encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f if line.strip()]