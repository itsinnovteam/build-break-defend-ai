"""Walk through the INDEXING pipeline one stage at a time.

    Internal Data --> Document Processing --> Chunking --> Embedding --> Vector DB

    python3 -m ragkit.pipeline data                       # 1. internal data
    python3 -m ragkit.pipeline process <doc>              # 2. document processing
    python3 -m ragkit.pipeline chunk <doc>                # 3. chunking
    python3 -m ragkit.pipeline embed "some text"          # 4. embedding
    python3 -m ragkit.ingest                              # 5. build the vector DB
    python3 -m ragkit.pipeline vectordb                   #    ...and inspect it

<doc> is a file name in data/docs, with or without .md; a unique prefix works
(e.g. "restricted-insider").
"""
from __future__ import annotations

import argparse
import textwrap
from collections import Counter
from pathlib import Path

from . import config
from .documents import chunk_document, load_corpus, parse_front_matter
from .embeddings import LexicalEmbedder, choose_embedder, preview


def find_doc(name: str) -> Path:
    name = name[:-3] if name.endswith(".md") else name
    matches = [p for p in sorted(config.DOCS_DIR.glob("*.md")) if p.stem.startswith(name)]
    exact = [p for p in matches if p.stem == name]
    if exact:
        return exact[0]
    if len(matches) == 1:
        return matches[0]
    options = "\n  ".join(p.stem for p in (matches or sorted(config.DOCS_DIR.glob("*.md"))))
    raise SystemExit("Pick one document:\n  " + options)


def cmd_data(_args) -> None:
    print("STAGE 1 - INTERNAL DATA  ({})\n".format(config.DOCS_DIR.relative_to(config.ROOT)))
    print("{:<38} {:<11} {:>6}  {}".format("DOCUMENT", "LABEL", "BYTES", "ALLOWED GROUPS"))
    print("-" * 96)
    for p in sorted(config.DOCS_DIR.glob("*.md")):
        meta, _ = parse_front_matter(p.read_text(encoding="utf-8"))
        print("{:<38} {:<11} {:>6}  {}".format(
            p.stem, meta.get("classification", "?"), p.stat().st_size, ", ".join(meta.get("allowed_groups", []))))


def cmd_process(args) -> None:
    path = find_doc(args.doc)
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)
    print("STAGE 2 - DOCUMENT PROCESSING: {}\n".format(path.name))
    print("Metadata extracted from the front matter (this is the access-control label):")
    for k, v in meta.items():
        print("  {:<16} {}".format(k + ":", ", ".join(v) if isinstance(v, list) else v))
    print("\nClean text kept for search: {} characters (raw file: {})".format(len(body.strip()), len(raw)))
    print(textwrap.indent(textwrap.shorten(" ".join(body.split()), 300), "  "))


def cmd_chunk(args) -> None:
    path = find_doc(args.doc)
    inherit = config.load_policy()["fix3_inherit_chunk_labels"]
    chunks = chunk_document(path, inherit_labels=inherit)
    print("STAGE 3 - CHUNKING: {}  ->  {} chunk(s), split on '## ' headings\n".format(path.name, len(chunks)))
    for c in chunks:
        print("{}  section: {}".format(c.id, c.section))
        print("  label: {} / allowed: {}".format(c.classification, ", ".join(c.allowed_groups)))
        print(textwrap.indent(textwrap.shorten(c.text, 160), "  text: "))
        print()
    print("Labelling policy: {}".format("FIX-3 ON" if inherit else "vulnerable (look closely at the labels!)"))


def cmd_embed(args) -> None:
    embedder = choose_embedder(args.embedder)
    if isinstance(embedder, LexicalEmbedder):
        # TF-IDF needs to learn word weights from the corpus first.
        embedder.fit([c.title + "\n" + c.section + "\n" + c.text for c in load_corpus(True)])
    print("STAGE 4 - EMBEDDING with '{}'\n".format(embedder.name))
    for text in args.text:
        print('"{}"'.format(text))
        print("  -> " + preview(embedder.embed_query(text), 5) + "\n")
    print("Similar meaning -> similar vectors. Retrieval compares these numbers, not the words.")


def cmd_vectordb(_args) -> None:
    from .store import VectorStore
    store = VectorStore.load()
    labels = Counter(c.classification for c in store.chunks)
    print("STAGE 5 - VECTOR DB  ({})\n".format(config.INDEX_FILE.relative_to(config.ROOT)))
    print("  embedder : {}".format(store.embedder.name))
    print("  chunks   : {} from {} documents".format(len(store.chunks), len({c.doc_id for c in store.chunks})))
    print("  labels   : " + ", ".join("{} {}".format(n, k) for k, n in sorted(labels.items())))
    print("  example  : {}".format(store.chunks[0].id))
    print("             vector {}".format(preview(store.vectors[0])))
    print("             metadata: label={}, allowed={}".format(
        store.chunks[0].classification, ", ".join(store.chunks[0].allowed_groups)))
    print("\nEach entry = vector + text + metadata. The metadata is the only thing a")
    print("permission filter can check at query time.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore the indexing pipeline stage by stage")
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("data", help="1. list the internal data")
    p = sub.add_parser("process", help="2. extract metadata and clean text from one document")
    p.add_argument("doc")
    p = sub.add_parser("chunk", help="3. split one document into chunks")
    p.add_argument("doc")
    p = sub.add_parser("embed", help="4. turn text into a vector")
    p.add_argument("text", nargs="+")
    p.add_argument("--embedder", choices=["auto", "ollama", "lexical"], default="auto")
    sub.add_parser("vectordb", help="5. inspect the built vector DB")
    args = parser.parse_args()
    {"data": cmd_data, "process": cmd_process, "chunk": cmd_chunk,
     "embed": cmd_embed, "vectordb": cmd_vectordb}[args.stage](args)


if __name__ == "__main__":
    main()
