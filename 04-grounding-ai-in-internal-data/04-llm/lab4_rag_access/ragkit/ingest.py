"""Build the vector index:  python3 -m ragkit.ingest [--embedder auto|ollama|lexical]

Prints every chunk with its label so you can check what the retriever will
believe about each piece of text.
"""
from __future__ import annotations

import argparse
import time

from . import config
from .documents import load_corpus
from .embeddings import choose_embedder
from .store import VectorStore


def build_index(embedder_choice: str = "auto", quiet: bool = False) -> VectorStore:
    policy = config.load_policy()
    inherit = policy["fix3_inherit_chunk_labels"]
    chunks = load_corpus(inherit_labels=inherit)
    embedder = choose_embedder(embedder_choice)
    if not quiet:
        print("Embedding {} chunks with '{}' ...".format(len(chunks), embedder.name))
    start = time.time()
    vectors = embedder.embed_documents([c.title + "\n" + c.section + "\n" + c.text for c in chunks])
    store = VectorStore(chunks, vectors, embedder, {"fix3_inherit_chunk_labels": inherit})
    store.save()
    if not quiet:
        print("Done in {:.1f}s -> {}\n".format(time.time() - start, config.INDEX_FILE.relative_to(config.ROOT)))
        print("{:<38} {:<26} {:<11} {}".format("CHUNK", "SECTION", "LABEL", "ALLOWED GROUPS"))
        print("-" * 100)
        for c in chunks:
            print("{:<38} {:<26} {:<11} {}".format(
                c.id[:38], c.section[:26], c.classification, ", ".join(c.allowed_groups)))
        print("\nChunk labelling policy: {}".format(
            "FIX-3 ON (labels inherited from the document)" if inherit
            else "VULNERABLE (labels read per section)"))
    return store


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Lab 4 vector index")
    parser.add_argument("--embedder", choices=["auto", "ollama", "lexical"], default="auto")
    args = parser.parse_args()
    build_index(args.embedder)


if __name__ == "__main__":
    main()
