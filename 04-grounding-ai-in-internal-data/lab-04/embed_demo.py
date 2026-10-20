"""
embed_demo.py - Section 4.2: what an embedding is, and how similarity search uses it.

  1. One sentence -> 384 numbers (a vector)
  2. Similar MEANING -> high cosine similarity, even with no shared words
  3. A 2-D map of the vectors, for teaching only (it distorts distances!)
  4. Similarity search over our index, as user 'ana'

Run:  python embed_demo.py      (no chat model needed: only the small embedding model)
"""

import math
import sys

import identity
import ollama_client
from keyword_search import tokenize
from vectorstore import VectorStore, cosine

SENTENCES = [
    ("S1", "My father is in the hospital and I need a few days off work."),
    ("S2", "How do I apply for emergency leave?"),
    ("S3", "I cannot connect to the company network from home."),
    ("S4", "The VPN client shows error 809."),
    ("S5", "Ransomware encrypted the file server."),
    ("S6", "All files on the server were locked and a ransom note appeared."),
    ("S7", "The canteen serves adobo on Fridays."),
]
SEARCH_QUESTION = "My father is in the hospital and I need a few days off work."


def pca_2d(vectors, iterations=200):
    """Project vectors onto their 2 main directions (PCA by power iteration, plain Python)."""
    n, d = len(vectors), len(vectors[0])
    mean = [sum(v[i] for v in vectors) / n for i in range(d)]
    centered = [[v[i] - mean[i] for i in range(d)] for v in vectors]
    axes = []
    for _ in range(2):
        axis = [1.0 / math.sqrt(d)] * d
        for _ in range(iterations):
            scores = [sum(a * b for a, b in zip(row, axis)) for row in centered]
            new = [sum(scores[j] * centered[j][i] for j in range(n)) for i in range(d)]
            for prev in axes:                     # stay at right angles to the first axis
                dot = sum(a * b for a, b in zip(new, prev))
                new = [a - dot * b for a, b in zip(new, prev)]
            length = math.sqrt(sum(a * a for a in new)) or 1.0
            axis = [a / length for a in new]
        axes.append(axis)
    return [tuple(round(sum(a * b for a, b in zip(row, ax)), 3) for ax in axes) for row in centered]


def ascii_map(points, labels, width=48, height=13):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    grid = [[" "] * width for _ in range(height)]
    for (x, y), label in zip(points, labels):
        col = int((x - min(xs)) / ((max(xs) - min(xs)) or 1) * (width - 4))
        row = int((max(ys) - y) / ((max(ys) - min(ys)) or 1) * (height - 1))
        for shift in (0, 1, -1, 2, -2, 3, -3):          # move a label that would overlap another
            r = min(max(row + shift, 0), height - 1)
            if all(grid[r][c] == " " for c in range(max(col - 1, 0), min(col + len(label) + 1, width))):
                row = r
                break
        for i, ch in enumerate(label):
            grid[row][col + i] = ch
    print("    +" + "-" * width + "+")
    for line in grid:
        print("    |" + "".join(line) + "|")
    print("    +" + "-" * width + "+")


def main():
    try:
        vectors = ollama_client.embed([s for _, s in SENTENCES])
    except ollama_client.OllamaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("1. ONE SENTENCE -> ONE VECTOR")
    print(f'   "{SENTENCES[1][1]}"')
    print(f"   -> {len(vectors[1])} numbers, first five: {[round(x, 3) for x in vectors[1][:5]]}")
    print("   The numbers have no meaning on their own; only distances between vectors matter.\n")

    print("2. COSINE SIMILARITY (1.00 = same direction, around 0 = unrelated)")
    for label, text in SENTENCES:
        print(f"   {label} {text}")
    print("\n        " + "".join(f"{lab:>7}" for lab, _ in SENTENCES))
    for (lab, _), a in zip(SENTENCES, vectors):
        print(f"   {lab:<5}" + "".join(f"{cosine(a, b):7.2f}" for b in vectors))
    shared = set(tokenize(SENTENCES[0][1])) & set(tokenize(SENTENCES[1][1]))
    print(f"\n   S1 vs S2: similarity {cosine(vectors[0], vectors[1]):.2f}, shared keywords: "
          f"{sorted(shared) if shared else 'none'}  -> meaning, not words")
    print(f"   S3 vs S4: similarity {cosine(vectors[2], vectors[3]):.2f}  -> two ways to describe a VPN problem")
    print(f"   S1 vs S7: similarity {cosine(vectors[0], vectors[6]):.2f}  -> unrelated, yet not 0: models are imperfect, so test with real questions\n")

    print("3. A 2-D MAP OF THE 384-D VECTORS (PCA) - for teaching only")
    points = pca_2d(vectors)
    ascii_map(points, [lab for lab, _ in SENTENCES])
    print("   2-D distance vs real similarity, for every pair:")
    pairs = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            pairs.append((math.dist(points[i], points[j]), cosine(vectors[i], vectors[j]),
                          SENTENCES[i][0], SENTENCES[j][0]))
    by_map = sorted(pairs)                                   # closest on the map first
    by_real = sorted(pairs, key=lambda p: -p[1])             # most similar in 384-D first
    rank_real = {(p[2], p[3]): n for n, p in enumerate(by_real, 1)}
    for dist, sim, a, b in by_map[:4]:
        print(f"   {a}-{b}: map distance {dist:.2f}, real similarity {sim:.2f} "
              f"(rank {rank_real[(a, b)]} of {len(pairs)} in the real space)")
    print("   Warning: squeezing 384 dimensions into 2 distorts distances. Two points that look")
    print("   close on a 2-D map (PCA or t-SNE) can be far apart in the real space, and the")
    print("   reverse. Measure retrieval with real questions (Section 4.3), never with a picture.\n")

    print(f"4. SIMILARITY SEARCH over the index, as user 'ana'")
    print(f'   Question: "{SEARCH_QUESTION}"')
    try:
        roles = identity.resolve_roles("ana")
        store = VectorStore().open()
        query = ollama_client.embed([SEARCH_QUESTION])[0]
        for score, chunk in store.search_filtered(query, roles, allow_local_only=True, k=3):
            print(f"   {score:.2f}  {chunk['chunk_id']:<10} {chunk['title']}")
        store.close()
    except (FileNotFoundError, identity.AccessDenied, ollama_client.OllamaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("   The question never says 'emergency leave', yet the HR policy comes first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
