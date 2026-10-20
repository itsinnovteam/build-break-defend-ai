"""
retrieval.py - the QUERY-TIME search: which chunks go into the prompt?

  mode "vector"  rank by cosine similarity between the question vector and chunk vectors
  mode "hybrid"  also rank by keywords (BM25) and merge both rankings with
                 Reciprocal Rank Fusion: score = 1/(60 + vector rank) + 1/(60 + keyword rank)

roles=None means NO access filter (the insecure v1 path). The secure v2 path always passes
the user's trusted roles, so the vector store filters BEFORE ranking (see vectorstore.py).

A relevance gate drops weak matches: if nothing is left, the assistant says it could not
find the answer instead of letting the model guess.
"""

import config
from keyword_search import bm25_scores  # noqa: F401  (also used by experiments.py)

RRF_K = 60            # standard constant for Reciprocal Rank Fusion
MIN_KEYWORD = 2.0     # hybrid: a chunk with a strong exact-word match also passes the gate
MODES = ("vector", "hybrid")


def retrieve(store, question, question_vector, roles=None, allow_local_only=True,
             mode="vector", k=None, min_similarity=None):
    """Return up to k hits, best first: [{"chunk", "similarity", "keyword", "score"}, ...]"""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    k = config.TOP_K if k is None else k
    min_similarity = config.MIN_SIMILARITY if min_similarity is None else min_similarity

    if roles is None:
        ranked = store.search_all(question_vector)                      # INSECURE: everything
    else:
        ranked = store.search_filtered(question_vector, roles, allow_local_only)   # SECURE
    hits = [{"chunk": c, "similarity": s, "keyword": 0.0, "score": s} for s, c in ranked]

    if mode == "vector":
        relevant = [h for h in hits if h["similarity"] >= min_similarity]
        return relevant[:k]

    keyword = bm25_scores([h["chunk"] for h in hits], question)
    for h in hits:
        h["keyword"] = keyword.get(h["chunk"]["chunk_id"], 0.0)
    by_keyword = sorted((h for h in hits if h["keyword"] > 0),
                        key=lambda h: (-h["keyword"], h["chunk"]["chunk_id"]))
    keyword_rank = {h["chunk"]["chunk_id"]: n for n, h in enumerate(by_keyword, 1)}
    for vector_rank, h in enumerate(hits, 1):
        fused = 1 / (RRF_K + vector_rank)
        if h["chunk"]["chunk_id"] in keyword_rank:
            fused += 1 / (RRF_K + keyword_rank[h["chunk"]["chunk_id"]])
        h["score"] = round(fused, 5)
    relevant = [h for h in hits if h["similarity"] >= min_similarity or h["keyword"] >= MIN_KEYWORD]
    relevant.sort(key=lambda h: (-h["score"], h["chunk"]["chunk_id"]))
    return relevant[:k]


def retrieve_then_filter(store, question, question_vector, roles, k=None):
    """
    ANTI-PATTERN, for the lesson only: take the top k of ALL documents, THEN drop the ones the
    user may not see. Restricted chunks take the top places, so allowed answers are lost, and
    the restricted text was already loaded and ranked for this user.
    """
    hits = retrieve(store, question, question_vector, roles=None, k=k)
    return [h for h in hits if set(h["chunk"]["allowed_roles"]) & set(roles)]
