"""Lab 4.3 - Embed and store: build the vector index.

For every chunk we ask the embedding model for a vector (a list of numbers
that captures the chunk's meaning) and save chunks + vectors to index.json.
A real system would use a vector database; a JSON file shows the same idea.

Run:
    python3 indexer.py                    # index docs/ (approved and not)
    python3 indexer.py --approved-only    # Lab 4.6 defence: approved docs only
"""
import argparse
import json
import time

import chunker
import config
import ollama_client

# nomic-embed-text works best when documents and questions carry these
# prefixes (see the model card). Other embedding models may not need them.
DOC_PREFIX = "search_document: "


def build_index(folder=config.DOCS_DIR, approved_only=False, batch_size=8):
    chunks = chunker.chunk_all(folder)
    if approved_only:
        skipped = [c["id"] for c in chunks if c["status"] != "approved"]
        chunks = [c for c in chunks if c["status"] == "approved"]
        for cid in skipped:
            print("  skipped (not approved): " + cid)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vectors = ollama_client.embed([DOC_PREFIX + c["text"] for c in batch])
        for c, v in zip(batch, vectors):
            c["embedding"] = v
        print("  embedded {}/{}".format(min(i + batch_size, len(chunks)), len(chunks)))
    return chunks


def save_index(chunks, path=config.INDEX_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"embed_model": config.EMBED_MODEL, "chunks": chunks}, f)


def load_index(path=config.INDEX_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["chunks"]


def main():
    parser = argparse.ArgumentParser(description="Lab 4.3: embed chunks and save the index")
    parser.add_argument("--folder", default=config.DOCS_DIR)
    parser.add_argument("--approved-only", action="store_true")
    args = parser.parse_args()

    start = time.time()
    chunks = build_index(args.folder, args.approved_only)
    save_index(chunks)
    dims = len(chunks[0]["embedding"]) if chunks else 0
    print("\nSaved {} chunks to {} ({} numbers per vector) in {:.1f}s".format(
        len(chunks), config.INDEX_FILE, dims, time.time() - start))
    if chunks:
        print("First 5 numbers of {}: {}".format(
            chunks[0]["id"], [round(x, 4) for x in chunks[0]["embedding"][:5]]))


if __name__ == "__main__":
    main()
