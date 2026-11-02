"""Shared helpers for the vector DB labs (DB1-DB7).

Every lab opens the same Chroma collection that indexer_chroma.py builds,
so run this first:
    python3 indexer_chroma.py
"""
import sys

import config
import indexer_chroma as db      # also applies the pysqlite3 fix before chromadb loads
import ollama_client


def collection():
    """Open the playbooks collection, or explain how to build it."""
    col = db.get_collection(db.get_client())
    if col.count() == 0:
        sys.exit("The collection is empty. Run:  python3 indexer_chroma.py")
    return col


def ask(col, question, where=None, n=config.TOP_K):
    """Semantic search. Returns a list of (score, id, text, metadata), best first.

    No MIN_SCORE cut-off here, so learners can see every score.
    """
    q_vec = ollama_client.embed([db.QUERY_PREFIX + question])[0]
    result = col.query(
        query_embeddings=[q_vec],
        n_results=n,
        where=where,
        include=["documents", "distances", "metadatas"],
    )
    return [
        (1.0 - dist, cid, text, meta or {})
        for cid, text, dist, meta in zip(
            result["ids"][0], result["documents"][0],
            result["distances"][0], result["metadatas"][0])
    ]


def show(hits, title=None):
    """Print search results in a readable block."""
    if title:
        print("\n--- " + title + " ---")
    if not hits:
        print("  (no results)")
    for score, cid, text, meta in hits:
        flag = "" if score >= config.MIN_SCORE else "   (below MIN_SCORE {})".format(config.MIN_SCORE)
        status = meta.get("status", "-")
        print("  {:.3f}  {}  [status: {}]{}".format(score, cid, status, flag))
        print("         " + " ".join(text.split())[:110])


def pause(message="Press Enter to continue..."):
    """Wait between steps when run in a terminal, so the class can follow."""
    if sys.stdin.isatty():
        input("\n" + message)
