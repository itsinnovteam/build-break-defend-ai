"""Lab 4.3 (extra) - See the embeddings: a t-SNE map of index.json.

Each chunk's embedding has 768 numbers - too many to picture. t-SNE squeezes
them onto a flat 2-D map while trying to keep chunks that were close in 768-D
close on the map. Same-colour dots = same document.

Run (after python3 indexer.py):
    python3 visualize_tsne.py               # writes tsne.svg
Then download tsne.svg and open it in a browser.

Standard library only (no numpy / sklearn), fine for a few hundred chunks.
How to read it: clusters and neighbours matter; exact positions and the
distances BETWEEN clusters do not. A different --seed gives a different
layout of the same groups.
"""
import argparse
import math
import random

import indexer

COLOURS = ["#2b6cb0", "#dd6b20", "#2f855a", "#b83280", "#6b46c1", "#c53030", "#2c7a7b", "#975a16"]


def sq_distances(vectors):
    # Normalise to length 1 so distance tracks cosine similarity (as in Lab 4.4).
    unit = []
    for v in vectors:
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        unit.append([x / n for x in v])
    n = len(unit)
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = sum((a - b) ** 2 for a, b in zip(unit[i], unit[j]))
            d[i][j] = d[j][i] = s
    return d


def affinities(d, perplexity):
    """P[i][j]: how likely i would pick j as a neighbour in the original space."""
    n = len(d)
    target = math.log(perplexity)
    p = [[0.0] * n for _ in range(n)]
    for i in range(n):
        lo, hi, beta = 0.0, float("inf"), 1.0
        for _ in range(60):                       # binary search for beta
            row = [0.0 if j == i else math.exp(-d[i][j] * beta) for j in range(n)]
            total = sum(row) or 1e-12
            entropy = math.log(total) + beta * sum(d[i][j] * row[j] for j in range(n)) / total
            if abs(entropy - target) < 1e-5:
                break
            if entropy > target:
                lo = beta
                beta = beta * 2 if hi == float("inf") else (beta + hi) / 2
            else:
                hi = beta
                beta = (beta + lo) / 2
        p[i] = [x / total for x in row]
    return [[(p[i][j] + p[j][i]) / (2 * n) for j in range(n)] for i in range(n)]


def tsne(vectors, perplexity=5.0, iterations=1000, seed=7):
    n = len(vectors)
    p = affinities(sq_distances(vectors), min(perplexity, (n - 1) / 3))
    rng = random.Random(seed)
    y = [[rng.gauss(0, 1e-4), rng.gauss(0, 1e-4)] for _ in range(n)]
    vel = [[0.0, 0.0] for _ in range(n)]
    lr = 100.0
    for it in range(iterations):
        exag = 4.0 if it < 100 else 1.0           # early exaggeration
        mom = 0.5 if it < 250 else 0.8
        num = [[0.0] * n for _ in range(n)]
        total = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = y[i][0] - y[j][0], y[i][1] - y[j][1]
                q = 1.0 / (1.0 + dx * dx + dy * dy)
                num[i][j] = num[j][i] = q
                total += 2 * q
        for i in range(n):
            gx = gy = 0.0
            for j in range(n):
                if i == j:
                    continue
                w = (exag * p[i][j] - num[i][j] / total) * num[i][j]
                gx += w * (y[i][0] - y[j][0])
                gy += w * (y[i][1] - y[j][1])
            vel[i][0] = mom * vel[i][0] - lr * 4 * gx
            vel[i][1] = mom * vel[i][1] - lr * 4 * gy
        for i in range(n):
            y[i][0] += vel[i][0]
            y[i][1] += vel[i][1]
    return y


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_svg(chunks, points, path, note):
    w, h, pad, legend_w = 960, 620, 60, 320
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    sx = lambda x: pad + (x - min(xs)) / ((max(xs) - min(xs)) or 1) * (w - legend_w - 2 * pad)
    sy = lambda v: pad + 30 + (v - min(ys)) / ((max(ys) - min(ys)) or 1) * (h - 2 * pad - 50)
    docs = []
    for c in chunks:
        if c["doc_id"] not in docs:
            docs.append(c["doc_id"])
    colour = {d: COLOURS[i % len(COLOURS)] for i, d in enumerate(docs)}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" font-family="Arial, sans-serif">'.format(w, h),
           '<rect width="100%" height="100%" fill="#fbfbf8"/>',
           '<text x="24" y="34" font-size="20" font-weight="bold" fill="#1a202c">Chunks from the same playbook land close together</text>',
           '<text x="24" y="56" font-size="13" fill="#4a5568">{}</text>'.format(esc(note))]
    for c, (x, y) in zip(chunks, points):
        label = c["id"].split("#", 1)[1]
        out.append('<circle cx="{:.1f}" cy="{:.1f}" r="7" fill="{}" fill-opacity="0.85"/>'.format(sx(x), sy(y), colour[c["doc_id"]]))
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="11" fill="#2d3748">{}</text>'.format(sx(x) + 10, sy(y) + 4, esc(label)))
    lx = w - legend_w + 20
    out.append('<text x="{}" y="100" font-size="13" font-weight="bold" fill="#1a202c">Document</text>'.format(lx))
    for i, d in enumerate(docs):
        title = next(c["title"] for c in chunks if c["doc_id"] == d)
        y = 126 + i * 40
        out.append('<circle cx="{}" cy="{}" r="7" fill="{}"/>'.format(lx + 7, y - 4, colour[d]))
        out.append('<text x="{}" y="{}" font-size="12" font-weight="bold" fill="#1a202c">{}</text>'.format(lx + 22, y, esc(d)))
        out.append('<text x="{}" y="{}" font-size="11" fill="#4a5568">{}</text>'.format(lx + 22, y + 15, esc(title if len(title) <= 42 else title[:40] + "...")))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    parser = argparse.ArgumentParser(description="t-SNE map of the chunk embeddings")
    parser.add_argument("--out", default="tsne.svg")
    parser.add_argument("--perplexity", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    chunks = indexer.load_index()
    print("Running t-SNE on {} chunks ({} numbers each)...".format(len(chunks), len(chunks[0]["embedding"])))
    points = tsne([c["embedding"] for c in chunks], args.perplexity, seed=args.seed)
    note = "t-SNE of {} chunk embeddings ({}-D to 2-D). Neighbours matter; distances between clusters do not.".format(
        len(chunks), len(chunks[0]["embedding"]))
    write_svg(chunks, points, args.out, note)
    print("Saved " + args.out + " - download it and open it in a browser.")


if __name__ == "__main__":
    main()
