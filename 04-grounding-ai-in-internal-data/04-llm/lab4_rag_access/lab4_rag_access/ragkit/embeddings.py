"""Turn text into vectors.

Two embedders are provided:

* OllamaEmbedder  - a real embedding model (default: nomic-embed-text) served
                    by the local Ollama. This is what production RAG uses.
* LexicalEmbedder - TF-IDF keyword vectors in pure Python. No model needed.
                    Used automatically when the embedding model is missing.

Both return L2-normalised vectors so cosine similarity is a plain dot product.
"""
from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from collections import Counter
from typing import Dict, List, Union

from . import config

Vector = Union[List[float], Dict[str, float]]

STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i if in into is it its "
    "me my of on or our so that the their them then there these this to us was we were "
    "what when where which who why will with you your about any all also".split()
)


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 1]


def similarity(a: Vector, b: Vector) -> float:
    if isinstance(a, dict):
        if len(a) > len(b):
            a, b = b, a
        return sum(w * b.get(t, 0.0) for t, w in a.items())
    return sum(x * y for x, y in zip(a, b))


def _normalise_dense(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class LexicalEmbedder:
    name = "lexical"

    def __init__(self, idf: Dict[str, float] = None):
        self.idf: Dict[str, float] = idf or {}

    def fit(self, texts: List[str]) -> None:
        df: Counter = Counter()
        for text in texts:
            df.update(set(tokenize(text)))
        n = len(texts)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}

    def _embed(self, text: str) -> Dict[str, float]:
        counts = Counter(tokenize(text))
        vec = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in counts.items()}
        vec = {t: w for t, w in vec.items() if w > 0}
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        return {t: w / norm for t, w in vec.items()}

    def embed_documents(self, texts: List[str]) -> List[Vector]:
        if not self.idf:
            self.fit(texts)
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> Vector:
        return self._embed(text)

    def state(self) -> Dict:
        return {"idf": self.idf}


class OllamaEmbedder:
    def __init__(self, model: str = config.EMBED_MODEL):
        self.model = model
        self.name = "ollama:" + model

    def _post(self, path: str, payload: Dict) -> Dict:
        req = urllib.request.Request(
            config.OLLAMA_URL + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _embed_many(self, texts: List[str]) -> List[List[float]]:
        try:
            data = self._post("/api/embed", {"model": self.model, "input": texts})
            return [_normalise_dense(v) for v in data["embeddings"]]
        except urllib.error.HTTPError as err:
            if err.code != 404:
                raise
        # Older Ollama versions only have /api/embeddings (one text per call).
        out = []
        for text in texts:
            data = self._post("/api/embeddings", {"model": self.model, "prompt": text})
            out.append(_normalise_dense(data["embedding"]))
        return out

    # nomic-embed-text expects these task prefixes; other models ignore them.
    def embed_documents(self, texts: List[str]) -> List[Vector]:
        vectors: List[Vector] = []
        for i in range(0, len(texts), 8):
            vectors.extend(self._embed_many(["search_document: " + t for t in texts[i:i + 8]]))
        return vectors

    def embed_query(self, text: str) -> Vector:
        return self._embed_many(["search_query: " + text])[0]

    def state(self) -> Dict:
        return {"model": self.model}


def ollama_has_model(model: str) -> bool:
    try:
        with urllib.request.urlopen(config.OLLAMA_URL + "/api/tags", timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False
    names = {m.get("name", "") for m in tags.get("models", [])}
    return model in names or (model + ":latest") in names


def choose_embedder(choice: str = "auto"):
    if choice == "lexical":
        return LexicalEmbedder()
    if choice == "ollama":
        return OllamaEmbedder()
    if ollama_has_model(config.EMBED_MODEL):
        return OllamaEmbedder()
    print("[info] Embedding model '{}' not found in Ollama - using the built-in "
          "lexical (TF-IDF) embedder instead.".format(config.EMBED_MODEL))
    return LexicalEmbedder()


def embedder_from_state(name: str, state: Dict):
    if name == "lexical":
        return LexicalEmbedder(idf=state.get("idf"))
    return OllamaEmbedder(model=state.get("model", config.EMBED_MODEL))


def preview(vec: Vector, n: int = 3) -> str:
    """Short human-readable view of a vector, e.g. {0.12, -0.03, 0.10, ...}."""
    if isinstance(vec, dict):
        top = sorted(vec.items(), key=lambda kv: kv[1], reverse=True)[:n]
        terms = ", ".join("{}: {:.2f}".format(t, w) for t, w in top)
        return "{{{}, ...}}  (sparse: {} non-zero term{})".format(terms, len(vec), "" if len(vec) == 1 else "s")
    nums = ", ".join("{:.2f}".format(v) for v in vec[:n])
    return "{{{}, ...}}  ({} dimensions)".format(nums, len(vec))
