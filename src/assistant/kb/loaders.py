"""Load knowledge-base articles from markdown files with a front matter header.

Expected file layout:

    ---
    id: account
    title: Managing your account
    ---
    # Managing your account
    ## Section heading
    ...
"""

from pathlib import Path

from src.assistant.kb.schema import Document

REQUIRED_FIELDS = ("id", "title")


def parse_front_matter(text: str, path: Path) -> tuple[dict, str]:
    """Split a file into its front matter fields and the body."""
    if not text.startswith("---"):
        raise ValueError(f"{path}: file must start with a '---' front matter block")
    _, header, body = text.split("---", 2)

    fields = {}
    for line in header.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    missing = [name for name in REQUIRED_FIELDS if not fields.get(name)]
    if missing:
        raise ValueError(f"{path}: missing front matter fields {missing}")
    return fields, body.strip()


def load_markdown(kb_dir: Path | str) -> list[Document]:
    """Read every article in kb_dir (README.md is skipped), sorted by file name."""
    docs = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        fields, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
        docs.append(Document(id=fields["id"], title=fields["title"], body=body, path=str(path)))

    ids = [doc.id for doc in docs]
    duplicates = {doc_id for doc_id in ids if ids.count(doc_id) > 1}
    if duplicates:
        raise ValueError(f"duplicate document ids: {sorted(duplicates)}")
    return docs