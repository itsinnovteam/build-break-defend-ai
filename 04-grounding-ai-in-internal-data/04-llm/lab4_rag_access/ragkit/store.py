"""A tiny vector store saved as JSON.

Real deployments use a vector database (Chroma, pgvector, OpenSearch, Oracle
AI Vector Search...). The security question is the same everywhere: does the
search apply the caller's permissions BEFORE results are returned?
"""
from __future__ import annotations

import json
from typing import Callable, Dict, List, Optional, Tuple

from . import config
from .documents import Chunk
from .embeddings import Vector, embedder_from_state, similarity


class VectorStore:
    def __init__(self, chunks: List[Chunk], vectors: List[Vector], embedder, meta: Dict):
        self.chunks = chunks
        self.vectors = vectors
        self.embedder = embedder
        self.meta = meta  # e.g. which chunking policy built this index

    def search(
        self,
        query_vec: Vector,
        k: int = config.TOP_K,
        allow: Optional[Callable[[Chunk], bool]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Return the top-k chunks. If `allow` is given, chunks the caller may
        not see are dropped BEFORE ranking, so they can never be returned."""
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
            if allow is not None and not allow(chunk):
                continue
            scored.append((chunk, similarity(query_vec, vec)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k]

    def save(self) -> None:
        payload = {
            "meta": self.meta,
            "embedder": {"name": self.embedder.name, "state": self.embedder.state()},
            "chunks": [c.to_dict() for c in self.chunks],
            "vectors": self.vectors,
        }
        with config.INDEX_FILE.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    @classmethod
    def load(cls) -> "VectorStore":
        if not config.INDEX_FILE.exists():
            raise SystemExit("No index found. Run:  python3 -m ragkit.ingest")
        with config.INDEX_FILE.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        embedder = embedder_from_state(payload["embedder"]["name"], payload["embedder"]["state"])
        chunks = [Chunk.from_dict(c) for c in payload["chunks"]]
        return cls(chunks, payload["vectors"], embedder, payload.get("meta", {}))
