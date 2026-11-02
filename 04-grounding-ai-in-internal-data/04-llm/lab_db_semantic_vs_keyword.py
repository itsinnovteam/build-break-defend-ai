"""Lab DB2 - Semantic search vs keyword search.

Asks the same question two ways over the same playbook chunks:
  1. Keyword search: counts how many question words appear in each chunk.
  2. Semantic search: asks Chroma for the chunks closest in meaning.

The default question shares almost no words with the playbooks, so keyword
search struggles while semantic search still finds the right chunk.

Run:
    python3 lab_db2_semantic_vs_keyword.py
    python3 lab_db2_semantic_vs_keyword.py "your own question"
"""
import re
import sys

import config
import lab_common

DEFAULT_QUESTION = "Who do I tell if an admin login gets hacked?"

# Common words that would match everything and hide the point of the demo.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "be", "to", "of", "in", "on", "for",
    "and", "or", "if", "it", "i", "do", "does", "my", "me", "we", "you", "what",
    "who", "how", "when", "where", "should", "can", "get", "gets", "with", "about",
}


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def keyword_search(col, question, n=config.TOP_K):
    data = col.get(include=["documents", "metadatas"])
    q_words = words(question)
    scored = []
    for cid, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        matches = q_words & words(text)
        scored.append((len(matches), cid, text, sorted(matches)))
    scored.sort(key=lambda s: s[0], reverse=True)
    return q_words, scored[:n]


def main():
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    col = lab_common.collection()
    print("Question: " + question)

    q_words, kw_hits = keyword_search(col, question)
    print("\n--- Keyword search (words looked for: {}) ---".format(", ".join(sorted(q_words))))
    if all(h[0] == 0 for h in kw_hits):
        print("  No chunk contains any of these words.")
    for count, cid, text, matches in kw_hits:
        print("  {} match(es)  {}  {}".format(count, cid, matches))
        print("         " + " ".join(text.split())[:110])

    lab_common.show(lab_common.ask(col, question), "Semantic search (Chroma)")

    print("\nKeyword search needs the same words. Semantic search matches meaning.")


if __name__ == "__main__":
    main()
