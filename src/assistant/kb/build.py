"""Build the chunk index from kb/*.md.

Run from the project root:  python -m src.assistant.kb.build --chunker heading

Writes data/index/<chunker>/chunks.jsonl and manifest.json. The manifest records
a hash of the knowledge base, so a stale index can be detected (later: an Airflow
task rebuilds the index when the hash changes).
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.assistant.kb.chunking import chunk_documents, get_chunker
from src.assistant.kb.loaders import load_markdown
from src.assistant.kb.store import save_chunks

ROOT = Path(__file__).resolve().parents[3]
KB_DIR = ROOT / "kb"
INDEX_DIR = ROOT / "data" / "index"


def kb_hash(kb_dir: Path = KB_DIR) -> str:
    """Short fingerprint of all articles: changes whenever any file changes."""
    digest = hashlib.sha256()
    for path in sorted(kb_dir.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def build(chunker_name: str = "heading", kb_dir: Path = KB_DIR, index_dir: Path = INDEX_DIR) -> Path:
    docs = load_markdown(kb_dir)
    chunker = get_chunker(chunker_name)
    chunks = chunk_documents(docs, chunker)

    out_dir = index_dir / chunker.name
    save_chunks(chunks, out_dir / "chunks.jsonl")
    manifest = {
        "chunker": chunker.name,
        "kb_hash": kb_hash(kb_dir),
        "documents": len(docs),
        "chunks": len(chunks),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chunker", default="heading")
    args = parser.parse_args()

    out_dir = build(args.chunker)
    print(json.loads((out_dir / "manifest.json").read_text()))
    print(f"saved to {out_dir.relative_to(ROOT)}")