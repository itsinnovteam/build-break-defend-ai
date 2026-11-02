"""Load Markdown documents and split them into labelled chunks.

Each document starts with a small front-matter block:

    ---
    title: ...
    classification: public | internal | restricted
    allowed_groups: [group-a, group-b]
    ---

The label (classification + allowed_groups) is what access control relies on.
If a chunk loses its label, the retriever can no longer protect it.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from . import config

FRONT_MATTER_RE = re.compile(r"^\s*---\n(.*?)\n---\n", re.S)
MAX_CHUNK_CHARS = 900

# What a chunk gets when no label can be found. "Fail open" defaults like this
# are a classic source of data leaks.
DEFAULT_LABEL = {"classification": "public", "allowed_groups": ["everyone"]}


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    section: str
    text: str
    classification: str
    allowed_groups: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Chunk":
        return cls(**data)


def parse_front_matter(text: str) -> Tuple[Dict, str]:
    """Return (metadata, body). Metadata is {} when there is no front matter."""
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: Dict = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value
    return meta, text[match.end():]


def split_sections(text: str) -> List[Tuple[str, str]]:
    """Split Markdown on '## ' headings. Text before the first heading is 'Overview'."""
    sections: List[Tuple[str, str]] = []
    name, lines = "Overview", []
    for line in text.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                sections.append((name, "\n".join(lines).strip()))
            name, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if "".join(lines).strip():
        sections.append((name, "\n".join(lines).strip()))
    return sections


def _split_long(text: str) -> List[str]:
    """Keep chunks small for a CPU-only model: split long sections on paragraphs."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    parts, current = [], ""
    for para in text.split("\n\n"):
        if current and len(current) + len(para) > MAX_CHUNK_CHARS:
            parts.append(current.strip())
            current = ""
        current += para + "\n\n"
    if current.strip():
        parts.append(current.strip())
    return parts


def document_label(path: Path) -> Dict:
    """Ground truth label of a whole document (used by the attack checker)."""
    meta, _ = parse_front_matter(path.read_text(encoding="utf-8"))
    return {
        "title": meta.get("title", path.stem),
        "classification": meta.get("classification", DEFAULT_LABEL["classification"]),
        "allowed_groups": meta.get("allowed_groups", DEFAULT_LABEL["allowed_groups"]),
    }


def chunk_document(path: Path, inherit_labels: bool) -> List[Chunk]:
    raw = path.read_text(encoding="utf-8")
    doc_id = path.stem
    pieces: List[Tuple[str, str, Dict]] = []  # (section, text, label-meta)

    if inherit_labels:
        # LAB4-FIX-3: read the label ONCE for the whole document, then stamp it
        # on every chunk. A chunk can never end up with a weaker label than its
        # document.
        meta, body = parse_front_matter(raw)
        for section, text in split_sections(body):
            pieces.append((section, text, meta))
    else:
        # LAB4-BUG-3: the raw file (front matter included) is split first, and
        # each section then looks for its OWN front matter. Only the first
        # section contains it, so every later section falls back to
        # DEFAULT_LABEL (public / everyone). Looks harmless, leaks a lot.
        for section, text in split_sections(raw):
            meta, body = parse_front_matter(text)
            pieces.append((section, body.strip(), meta))

    chunks: List[Chunk] = []
    for section, text, meta in pieces:
        for part in _split_long(text):
            chunks.append(
                Chunk(
                    id="{}#{}".format(doc_id, len(chunks)),
                    doc_id=doc_id,
                    title=meta.get("title", doc_id),
                    section=section,
                    text=part,
                    classification=meta.get("classification", DEFAULT_LABEL["classification"]),
                    allowed_groups=list(meta.get("allowed_groups", DEFAULT_LABEL["allowed_groups"])),
                )
            )
    return chunks


def load_corpus(inherit_labels: bool) -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in sorted(config.DOCS_DIR.glob("*.md")):
        chunks.extend(chunk_document(path, inherit_labels))
    return chunks


def ground_truth_labels() -> Dict[str, Dict]:
    return {p.stem: document_label(p) for p in sorted(config.DOCS_DIR.glob("*.md"))}
