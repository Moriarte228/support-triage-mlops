"""One chunk per '## ' section of a markdown article."""

import re

from src.assistant.kb.schema import Chunk, Document

_HEADING = re.compile(r"^## (.+)$", flags=re.MULTILINE)
_INTENTS = re.compile(r"<!--\s*intents:\s*(.*?)\s*-->")


def slugify(text: str) -> str:
    """'Why can't I send money?' -> 'why-cant-i-send-money'"""
    text = text.lower().replace("'", "").replace("\u2019", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


class HeadingChunker:
    """One chunk per '## ' section.

    The article title and the heading are prepended to the text, so a short
    section still carries its context. The intents label is moved from the
    text into metadata.
    """

    name = "heading"

    def split(self, doc: Document) -> list[Chunk]:
        # re.split with a capture group keeps the headings:
        # [text before the first ##, heading_1, body_1, heading_2, body_2, ...]
        parts = _HEADING.split(doc.body)
        chunks = []
        for heading, section in zip(parts[1::2], parts[2::2]):
            heading = heading.strip()
            match = _INTENTS.search(section)
            intents = [name.strip() for name in match.group(1).split(",") if name.strip()] if match else []
            body = _INTENTS.sub("", section).strip()
            chunks.append(
                Chunk(
                    id=f"{doc.id}#{slugify(heading)}",
                    doc_id=doc.id,
                    text=f"{doc.title} › {heading}\n{body}",
                    metadata={"title": doc.title, "heading": heading, "intents": intents, "source": doc.path},
                )
            )
        return chunks