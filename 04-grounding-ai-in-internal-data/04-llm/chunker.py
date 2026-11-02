"""Lab 4.2 - Load and chunk: turn playbooks into small, labelled pieces.

Each document starts with metadata lines (doc_id, title, version, status,
owner, last_reviewed, access), then Markdown. We split on "## " headings so
each chunk is one section, and split long sections by word count.

Run:
    python3 chunker.py              # chunks from docs/
    python3 chunker.py --show 3     # also print the first 3 chunks in full
"""
import argparse
import os
import re

import config

META_KEYS = ["doc_id", "title", "version", "status", "owner", "last_reviewed", "access"]


def load_documents(folder=config.DOCS_DIR):
    """Read every .md file in a folder. Returns a list of {meta, body, path}."""
    documents = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(folder, name)
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()

        meta = {}
        body_start = 0
        for i, line in enumerate(lines):
            key, sep, value = line.partition(":")
            if sep and key.strip() in META_KEYS:
                meta[key.strip()] = value.strip()
            else:
                body_start = i
                break
        meta.setdefault("doc_id", name[:-3])
        meta.setdefault("title", meta["doc_id"])
        meta.setdefault("version", "n/a")
        meta.setdefault("status", "unknown")
        meta.setdefault("access", "all-staff")
        documents.append({"meta": meta, "body": "\n".join(lines[body_start:]), "path": path})
    return documents


def split_words(text, max_words, overlap):
    """Split text into pieces of at most max_words, repeating `overlap` words."""
    words = text.split()
    if len(words) <= max_words:
        return [text.strip()]
    pieces, start = [], 0
    while start < len(words):
        pieces.append(" ".join(words[start:start + max_words]))
        if start + max_words >= len(words):
            break
        start += max_words - overlap
    return pieces


def chunk_document(doc, max_words=config.CHUNK_MAX_WORDS, overlap=config.CHUNK_OVERLAP_WORDS):
    """Split one document into chunks, one per "## " section (split further if long)."""
    sections = re.split(r"^## ", doc["body"], flags=re.MULTILINE)
    chunks = []
    for section in sections[1:]:              # sections[0] is the title area
        heading, _, text = section.partition("\n")
        heading = heading.strip()
        for n, piece in enumerate(split_words(text, max_words, overlap), start=1):
            slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
            chunk_id = "{}#{}".format(doc["meta"]["doc_id"], slug)
            if n > 1:
                chunk_id += "-{}".format(n)
            chunks.append({
                "id": chunk_id,
                "section": heading,
                # Put the title and heading IN the text: it helps the search
                # match questions like "escalation for suspicious login".
                "text": "{} - {}\n{}".format(doc["meta"].get("title", ""), heading, piece),
                **doc["meta"],
            })
    return chunks


def chunk_all(folder=config.DOCS_DIR):
    chunks = []
    for doc in load_documents(folder):
        chunks.extend(chunk_document(doc))
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Lab 4.2: load and chunk documents")
    parser.add_argument("--folder", default=config.DOCS_DIR)
    parser.add_argument("--show", type=int, default=0, help="print N chunks in full")
    args = parser.parse_args()

    docs = load_documents(args.folder)
    chunks = chunk_all(args.folder)
    print("Loaded {} documents, made {} chunks\n".format(len(docs), len(chunks)))
    print("{:<45} {:>6}  {}".format("CHUNK ID", "WORDS", "STATUS / ACCESS"))
    for c in chunks:
        print("{:<45} {:>6}  {} / {}".format(c["id"], len(c["text"].split()), c["status"], c["access"]))
    for c in chunks[:args.show]:
        print("\n" + "=" * 60 + "\n" + c["id"] + "\n" + "-" * 60 + "\n" + c["text"])


if __name__ == "__main__":
    main()
