"""
ingest.py - run the INDEXING pipeline: load -> clean -> chunk -> embed -> store.

Run it once, and again whenever a document (or its permissions) changes:
    python ingest.py
"""

import sys
import time

import config
import ollama_client
import pipeline
from vectorstore import VectorStore


def build_index(db_path=None, kb_dir=None, chunk_chars=None, overlap=None,
                embed=ollama_client.embed, embed_is_local=None):
    """Build the vector store. Returns a summary dict (used by this script and experiments.py)."""
    docs = pipeline.load_documents(kb_dir)                                   # 1 LOAD (+ 2 CLEAN)
    local = ollama_client.is_local() if embed_is_local is None else embed_is_local
    skipped = []
    if not local:   # data residency at INGEST time: never send local-only text to a remote service
        skipped = [d["doc_id"] for d in docs if d["residency"] == "local-only"]
        docs = [d for d in docs if d["residency"] != "local-only"]
    chunks = [c for d in docs for c in pipeline.chunk_document(d, chunk_chars, overlap)]   # 3 CHUNK
    started = time.time()
    vectors = embed([pipeline.embedding_input(c) for c in chunks])          # 4 EMBED
    seconds = time.time() - started
    store = VectorStore(db_path).create()                                   # 5 STORE
    try:
        for chunk, vector in zip(chunks, vectors):
            store.add(chunk, vector)
        store.set_info("kb_fingerprint", pipeline.kb_fingerprint(kb_dir))
        store.set_info("embed_model", config.EMBED_MODEL)
        store.set_info("chunk_chars", chunk_chars or config.CHUNK_CHARS)
        store.set_info("chunk_overlap", config.CHUNK_OVERLAP if overlap is None else overlap)
    finally:
        store.close()
    return {"docs": docs, "chunks": chunks, "seconds": seconds, "skipped": skipped, "local": local}


def main():
    print("Lab 4 - ingest (the indexing pipeline)")
    try:
        local = ollama_client.is_local()
        where = "local: no text leaves this VM" if local else "REMOTE: local-only documents will be skipped"
        print(f"Embedding model : {config.EMBED_MODEL} via {config.OLLAMA_URL} ({where})")
        summary = build_index()
    except (pipeline.DocumentError, ollama_client.OllamaError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    docs, chunks = summary["docs"], summary["chunks"]
    print(f"1 LOAD   {len(docs)} documents from kb/ (metadata checked)")
    print("2 CLEAN  text normalized (characters, spaces, headings)")
    print(f"3 CHUNK  {len(chunks)} chunks (up to {config.CHUNK_CHARS} characters, overlap {config.CHUNK_OVERLAP})")
    print(f"4 EMBED  {len(chunks)} vectors x {config.EMBED_DIMENSIONS} numbers in {summary['seconds']:.1f} s")
    print("5 STORE  index/vectors.db (folder permissions 700, file 600)")
    for doc_id in summary["skipped"]:
        print(f"         skipped {doc_id}: local-only, and the embedding service is not local")
    print()
    print(f"{'doc_id':<10} {'classification':<15} {'residency':<11} {'allowed roles':<25} chunks")
    for d in docs:
        n = sum(1 for c in chunks if c["doc_id"] == d["doc_id"])
        narrowed = [c for c in chunks if c["doc_id"] == d["doc_id"] and c["allowed_roles"] != d["allowed_roles"]]
        note = f"  ({len(narrowed)} chunk: {', '.join(narrowed[0]['allowed_roles'])} only)" if narrowed else ""
        print(f"{d['doc_id']:<10} {d['classification']:<15} {d['residency']:<11} "
              f"{', '.join(d['allowed_roles']):<25} {n}{note}")
    print("\nReady. Next: python embed_demo.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
