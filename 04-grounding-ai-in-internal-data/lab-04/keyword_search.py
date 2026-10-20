"""
keyword_search.py - classic keyword ranking (BM25), used for HYBRID search.

Vector search matches meaning ("my mother is in hospital" ~ "emergency leave").
Keyword search matches exact words and codes ("HR-F-12", "CVE-2024-3400", "SEC-EXC").
Hybrid search runs both and merges the two rankings (see retrieval.py).

BM25 is computed over the candidate chunks it is GIVEN. The secure assistant gives it
only the chunks the user may see, so the keyword path cannot leak either.
"""

import math
import re

STOPWORDS = set("""a about after all also am an and any are as at be been before by can could
do does for from has have how i if in into is it its may me must my no not of on or our
should so than that the their them then there these they this to us was we what when where
which who why will with you your""".split())


def tokenize(text):
    """Lower-case words and codes (HR-F-12 stays one token), without stop words."""
    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]                      # plural -> singular, very roughly
        out.append(w)
    return out


def bm25_scores(chunks, question, k1=1.5, b=0.75):
    """Return {chunk_id: score} for the given chunks. 0 means no query word matched."""
    docs = {c["chunk_id"]: tokenize(c["title"] + " " + c["text"]) for c in chunks}
    if not docs:
        return {}
    avg_len = sum(len(t) for t in docs.values()) / len(docs)
    doc_freq = {}
    for terms in docs.values():
        for t in set(terms):
            doc_freq[t] = doc_freq.get(t, 0) + 1
    n = len(docs)
    scores = {}
    for cid, terms in docs.items():
        score = 0.0
        for q in set(tokenize(question)):
            tf = terms.count(q)
            if not tf:
                continue
            idf = math.log(1 + (n - doc_freq[q] + 0.5) / (doc_freq[q] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(terms) / avg_len))
        scores[cid] = round(score, 3)
    return scores
