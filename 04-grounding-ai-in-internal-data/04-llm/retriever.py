"""Lab 4.4 - Retrieve: find the chunks most similar to a question.

We embed the question the same way as the chunks, then score every chunk with
cosine similarity (1.0 = same direction/meaning, 0 = unrelated) and keep the
best ones.

Run:
    python3 retriever.py "who do I escalate a compromised admin account to?"
    python3 retriever.py "what is the SLA for a KEV vulnerability?" --k 5
    python3 retriever.py "insider threat case" --role tier1     # Lab 4.7
"""
import argparse
import math

import config
import indexer
import ollama_client

QUERY_PREFIX = "search_query: "   # pairs with indexer.DOC_PREFIX


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# Lab 4.7 challenge: which roles may read which access labels?
ROLE_ACCESS = {
    "tier1": {"all-staff", "it-all", "soc-all"},
    "tier2": {"all-staff", "it-all", "soc-all"},
    "ir-lead": {"all-staff", "it-all", "soc-all", "ir-leads"},
}


def is_allowed(chunk, role):
    """Return True if `role` may see this chunk.

    TODO (Lab 4.7): right now every role sees everything, including the
    restricted IR-SEC-010 procedure. Use ROLE_ACCESS and chunk["access"] so
    that a role only sees chunks whose access label it is allowed. An unknown
    role should see nothing. role=None means "no filtering" (labs 4.4-4.6).
    """
    return True


def retrieve(question, chunks, k=config.TOP_K, min_score=config.MIN_SCORE, role=None):
    """Return the top-k chunks for a question as (score, chunk) pairs."""
    q_vec = ollama_client.embed([QUERY_PREFIX + question])[0]
    visible = [c for c in chunks if role is None or is_allowed(c, role)]
    scored = sorted(((cosine(q_vec, c["embedding"]), c) for c in visible),
                    key=lambda pair: pair[0], reverse=True)
    return [(s, c) for s, c in scored[:k] if s >= min_score]


def main():
    parser = argparse.ArgumentParser(description="Lab 4.4: semantic search over the index")
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=config.TOP_K)
    parser.add_argument("--min-score", type=float, default=config.MIN_SCORE)
    parser.add_argument("--role", default=None)
    args = parser.parse_args()

    chunks = indexer.load_index()
    results = retrieve(args.question, chunks, args.k, args.min_score, args.role)
    print("QUESTION: {}\n".format(args.question))
    if not results:
        print("No chunk scored above {}. Nothing relevant found.".format(args.min_score))
    for rank, (score, c) in enumerate(results, start=1):
        print("{}. score={:.3f}  {}  (v{}, {})".format(rank, score, c["id"], c["version"], c["status"]))
        print("   " + c["text"].replace("\n", " ")[:160] + "...\n")


if __name__ == "__main__":
    main()
