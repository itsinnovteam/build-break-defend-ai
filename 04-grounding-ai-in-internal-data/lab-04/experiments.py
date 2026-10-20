"""
experiments.py - Section 4.3: measure RAG tradeoffs instead of guessing.

Each experiment builds a temporary index (your real index/ is not touched), asks the same
14 test questions, and checks whether the retrieved chunks contain the fact the answer needs.
No chat model is needed: these experiments measure RETRIEVAL quality only.

Run:  python experiments.py          (about 1 minute on a CPU)
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

import config
import ingest
import ollama_client
import pipeline
import retrieval
from vectorstore import VectorStore

# (question, document that answers it, a fact the retrieved text must contain)
EVAL = [
    ("How do I apply for emergency leave?", "HR-001", "HR-F-12"),
    ("My father is in the hospital. How many paid days off can I take?", "HR-001", "3 working days"),
    ("What is form HR-F-12 for?", "HR-001", "HR-F-12"),
    ("When does the CAB meet?", "ITOPS-001", "Tuesday at 14:00"),
    ("Can I deploy to production on a Friday?", "DEVOPS-001", "Fridays"),
    ("When should I roll back a release?", "DEVOPS-002", "1 percent"),
    ("How long can a Tenable risk exception last?", "SEC-003", "90 days"),
    ("Which host has CVE-2024-3400?", "SEC-002", "web-prod-03"),
    ("How fast must critical vulnerabilities be fixed?", "SEC-002", "15 days"),
    ("My account is locked. How long until it unlocks?", "GEN-001", "30 minutes"),
    ("The VPN shows error 809. What should I do?", "GEN-002", "809"),
    ("What do we do in the first 15 minutes of a ransomware attack?", "SEC-001", "isolate"),
    ("When are the servers patched?", "ITOPS-002", "second Saturday"),
    ("What is the SEC-EXC queue used for?", "SEC-003", "SEC-EXC"),
]
QUESTIONS = [q for q, _, _ in EVAL]


def evaluate(db_path, vectors, mode="vector", k=config.TOP_K):
    """Return (fact hits, document hits, average context tokens, misses)."""
    store = VectorStore(db_path).open()
    facts = docs = tokens = 0
    misses = []
    for (question, doc_id, fact), vector in zip(EVAL, vectors):
        if mode == "keyword":
            chunks = store.all_chunks()
            scores = retrieval.bm25_scores(chunks, question)
            ranked = sorted((c for c in chunks if scores[c["chunk_id"]] > 0),
                            key=lambda c: (-scores[c["chunk_id"]], c["chunk_id"]))[:k]
            hits = [{"chunk": c} for c in ranked]
        else:
            hits = retrieval.retrieve(store, question, vector, roles=None, mode=mode, k=k)
        text = " ".join(h["chunk"]["text"] for h in hits)
        found_fact = fact in text
        facts += found_fact
        docs += any(h["chunk"]["doc_id"] == doc_id for h in hits)
        tokens += sum(pipeline.estimate_tokens(h["chunk"]["text"]) for h in hits)
        if not found_fact:
            misses.append(question)
    store.close()
    return facts, docs, round(tokens / len(EVAL)), misses


def build(folder, name, chunk_chars, overlap):
    db = Path(folder) / f"{name}.db"
    summary = ingest.build_index(db_path=db, chunk_chars=chunk_chars, overlap=overlap)
    return db, summary


def show_misses(misses):
    for q in misses:
        print(f"         missed: {q}")


def main():
    n = len(EVAL)
    print(f"RAG TRADEOFF EXPERIMENTS  ({n} test questions, embedding model {config.EMBED_MODEL})")
    print("fact@k = the retrieved chunks contain the fact the answer needs (higher is better)\n")
    folder = tempfile.mkdtemp(prefix="lab4-exp-")
    try:
        vectors = ollama_client.embed(QUESTIONS)

        print("E1  CHUNK SIZE (overlap 0, top-3, vector search)")
        print(f"    {'chunk size':<12}{'chunks':>7}{'fact@3':>9}{'avg tokens sent':>18}")
        for size in (150, 450, 900):
            db, s = build(folder, f"size{size}", size, 0)
            facts, _, tokens, misses = evaluate(db, vectors)
            print(f"    {size:<12}{len(s['chunks']):>7}{facts:>6}/{n}{tokens:>18}")
            show_misses(misses)

        print("\nE2  CHUNK OVERLAP (chunk size 150, top-3, vector search)")
        print(f"    {'overlap':<12}{'chunks':>7}{'fact@3':>9}{'stored characters':>20}")
        for overlap in (0, 60):
            db, s = build(folder, f"ov{overlap}", 150, overlap)
            facts, _, _, misses = evaluate(db, vectors)
            chars = sum(len(c["text"]) for c in s["chunks"])
            print(f"    {overlap:<12}{len(s['chunks']):>7}{facts:>6}/{n}{chars:>20,}")
            show_misses(misses)

        db, s = build(folder, "default", config.CHUNK_CHARS, config.CHUNK_OVERLAP)
        print(f"\nE3  TOP-K (chunk size {config.CHUNK_CHARS}, vector search)")
        print(f"    {'top-k':<12}{'fact@k':>9}{'avg tokens sent':>18}")
        for k in (1, 3, 5):
            facts, _, tokens, misses = evaluate(db, vectors, k=k)
            print(f"    {k:<12}{facts:>6}/{n}{tokens:>18}")
            show_misses(misses)

        print(f"\nE4  VECTOR vs KEYWORD vs HYBRID (chunk size {config.CHUNK_CHARS}, top-3)")
        for mode in ("vector", "keyword", "hybrid"):
            facts, _, _, misses = evaluate(db, vectors, mode=mode)
            print(f"    {mode:<12}{facts:>6}/{n}")
            show_misses(misses)

        print("\nE5  FRESHNESS - a document changes after the index was built")
        kb_copy = Path(folder) / "kb"
        shutil.copytree(config.KB_DIR, kb_copy)
        before = pipeline.kb_fingerprint(kb_copy)
        doc = kb_copy / "SEC-003_tenable_risk_exception.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("at most 90 days", "at most 60 days"),
                       encoding="utf-8")
        after = pipeline.kb_fingerprint(kb_copy)
        print(f"    fingerprint in the index : {before}")
        print(f"    fingerprint of kb/ now   : {after}   (policy changed: 90 -> 60 days)")
        print("    The index still says 90 days. ask.py (v2) refuses a stale index; ask_v1.py only warns.")
        print("    Fix: re-run ingest.py after every document or permission change (or on a schedule).")

        print("\nE6  CONTEXT WINDOW AND COST (estimates: about 4 characters per token)")
        all_text = sum(pipeline.estimate_tokens(d["body"]) for d in pipeline.load_documents())
        _, _, rag_tokens, _ = evaluate(db, vectors)
        print(f"    paste ALL {len(pipeline.load_documents())} documents into every prompt : about {all_text:,} tokens")
        print(f"    RAG top-3 chunks per question         : about {rag_tokens:,} tokens")
        print(f"    context window used in this lab       : {config.NUM_CTX:,} tokens (prompt + answer)")
        price = 3.00    # example price from Module 3: USD 3 per 1 million input tokens
        for label, t in (("paste all", all_text), ("RAG top-3", rag_tokens)):
            print(f"    {label:<10}: 1,000 questions/day x 30 days = USD {t * 30_000 * price / 1e6:,.2f}/month"
                  " (example hosted price; local Ollama costs no tokens)")
        started = time.time()
        ollama_client.embed(["How do I apply for emergency leave?"])
        print(f"    one question embedding took {1000 * (time.time() - started):.0f} ms on this machine")
    except (ollama_client.OllamaError, pipeline.DocumentError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
