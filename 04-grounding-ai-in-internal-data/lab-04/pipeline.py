"""
pipeline.py - the INDEXING pipeline, in small readable steps.

  1. LOAD     read each document in kb/ and its metadata header
  2. CLEAN    normalize the text (odd characters, extra spaces)
  3. CHUNK    cut the text into small pieces; every piece KEEPS the metadata
              (document id, department, classification, allowed roles, residency)
  4. EMBED    turn every chunk into a vector          -> ingest.py calls Ollama
  5. STORE    save chunks + vectors + metadata        -> vectorstore.py

Steps 4 and 5 are in ingest.py so that this file needs no AI and is easy to test.
"""

import hashlib
import re
import unicodedata
from pathlib import Path

import config

REQUIRED_FIELDS = ("doc_id", "title", "department", "classification",
                   "allowed_roles", "residency", "owner", "updated")
SECTION_MARKER = "@@ section_roles:"


class DocumentError(ValueError):
    """A document is missing metadata or has invalid metadata. Fail closed: do not index it."""


def _split_roles(text):
    return [r.strip() for r in text.split(",") if r.strip()]


# ---------- 1. LOAD -----------------------------------------------------------
def parse_document(path):
    """Read one document: a header between '---' lines, then the text."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if not raw.startswith("---") or len(parts) < 3:
        raise DocumentError(f"{path.name}: must start with a metadata header between '---' lines")
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    missing = [f for f in REQUIRED_FIELDS if not meta.get(f)]
    if missing:
        raise DocumentError(f"{path.name}: metadata is missing {', '.join(missing)}")
    if not re.fullmatch(r"[A-Z]+-\d{3}", meta["doc_id"]):
        raise DocumentError(f"{path.name}: doc_id must look like HR-001")
    if meta["classification"] not in config.CLASSIFICATIONS:
        raise DocumentError(f"{path.name}: classification must be one of {', '.join(config.CLASSIFICATIONS)}")
    if meta["residency"] not in config.RESIDENCY_VALUES:
        raise DocumentError(f"{path.name}: residency must be 'any' or 'local-only'")
    roles = _split_roles(meta["allowed_roles"])
    unknown = [r for r in roles if r not in config.KNOWN_ROLES]
    if not roles or unknown:
        raise DocumentError(f"{path.name}: allowed_roles has unknown or no roles: {unknown or 'none'}")
    meta["allowed_roles"] = roles
    meta["file"] = path.name
    meta["body"] = parts[2]
    return meta


def load_documents(folder=None):
    folder = Path(folder or config.KB_DIR)
    docs = [parse_document(p) for p in sorted(folder.glob("*.md"))]
    if not docs:
        raise DocumentError(f"No .md documents found in {folder}")
    ids = [d["doc_id"] for d in docs]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise DocumentError(f"Duplicate doc_id: {', '.join(duplicates)}")
    return docs


def kb_fingerprint(folder=None):
    """One short hash of all documents. It changes when any document (or its permissions) changes."""
    h = hashlib.sha256()
    for p in sorted(Path(folder or config.KB_DIR).glob("*.md")):
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


# ---------- 2. CLEAN ----------------------------------------------------------
_INVISIBLE = re.compile("[​‌‍⁠﻿]")      # zero-width characters
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(text):
    """Normalize characters, drop markdown heading marks and squeeze spaces. Paragraphs stay."""
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text).replace("\r\n", "\n").replace("\t", " ")
    text = _CONTROL.sub("", text)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"^#+\s*", "", line.strip())     # '# Title' -> 'Title'
        lines.append(re.sub(r" {2,}", " ", line))
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------- 3. CHUNK ----------------------------------------------------------
def split_sections(doc):
    """
    Split the body into sections. A line '@@ section_roles: hr' starts a section that only
    those roles may see (chunk-level permission). A section can NARROW the document's roles,
    never widen them (least privilege).
    """
    sections, roles, lines = [], list(doc["allowed_roles"]), []
    for line in doc["body"].split("\n"):
        if line.strip().startswith(SECTION_MARKER):
            sections.append((roles, "\n".join(lines)))
            roles = _split_roles(line.strip()[len(SECTION_MARKER):])
            wider = [r for r in roles if r not in doc["allowed_roles"]]
            if not roles or wider:
                raise DocumentError(f"{doc['file']}: section_roles must be a subset of allowed_roles "
                                    f"({', '.join(doc['allowed_roles'])})")
            lines = []
        else:
            lines.append(line)
    sections.append((roles, "\n".join(lines)))
    return [(r, clean_text(t)) for r, t in sections if clean_text(t)]


def _pieces(text, size):
    """Paragraphs, with very long paragraphs cut at word boundaries."""
    out = []
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        para = " ".join(para.split("\n"))
        while len(para) > size:
            cut = para.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            out.append(para[:cut].strip())
            para = para[cut:].strip()
        if para:
            out.append(para)
    return out


def _tail(text, overlap):
    """The last `overlap` characters of a chunk, starting at a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return text if overlap > 0 else ""
    cut = text.find(" ", len(text) - overlap)
    return text[cut + 1:] if cut != -1 else text[-overlap:]


def chunk_document(doc, chunk_chars=None, overlap=None):
    """Pack whole paragraphs into chunks of about chunk_chars characters, with optional overlap."""
    size = chunk_chars or config.CHUNK_CHARS
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
    if size < 100 or not 0 <= overlap < size // 2:
        raise ValueError("chunk_chars must be >= 100 and overlap must be between 0 and chunk_chars/2")
    chunks = []
    for roles, text in split_sections(doc):
        current, carried = "", ""
        for piece in _pieces(text, size):
            if current and len(current) + 1 + len(piece) > size:
                chunks.append((roles, current))
                carried = _tail(current, overlap)
                current = (carried + " " + piece) if carried else piece
            else:
                current = (current + " " + piece) if current else piece
        if current:
            chunks.append((roles, current))
    result = []
    for n, (roles, text) in enumerate(chunks, 1):
        result.append({
            "chunk_id": f"{doc['doc_id']}#{n}",
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "department": doc["department"],
            "classification": doc["classification"],
            "allowed_roles": list(roles),
            "residency": doc["residency"],
            "owner": doc["owner"],
            "text": text,
        })
    return result


def embedding_input(chunk):
    """What we give the embedding model: the title helps the vector know the topic."""
    return f"{chunk['title']}\n{chunk['text']}"


def estimate_tokens(text):
    """Rule of thumb from Module 3: about 4 characters per token in English."""
    return max(1, round(len(text) / 4))
