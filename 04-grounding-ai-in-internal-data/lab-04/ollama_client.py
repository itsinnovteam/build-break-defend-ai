"""
ollama_client.py - a tiny client for the local Ollama API (Python standard library only).

Same idea as Lab 3: our program sends JSON to Ollama and reads JSON back.
Two calls are used in Lab 4:
  embed(texts)    -> POST /api/embed  : turns text into vectors (the embedding model)
  chat(messages)  -> POST /api/chat   : writes the answer      (the chat model)
"""

import http.client
import json
import math
from urllib.parse import urlparse

import config

TIMEOUT_SECONDS = 600   # a CPU can need a few minutes for one chat answer


class OllamaError(Exception):
    """Ollama cannot be reached, or it answered with an error."""


def _address():
    url = urlparse(config.OLLAMA_URL)
    if url.scheme != "http" or not url.hostname:
        raise OllamaError(f"LAB4_OLLAMA_URL must look like http://127.0.0.1:11434 (got {config.OLLAMA_URL!r})")
    return url.hostname, url.port or 11434


def is_local():
    """True when Ollama runs on this machine, so no text leaves the VM."""
    host, _ = _address()
    return host in ("127.0.0.1", "localhost", "::1")


def _call(method, path, body=None, timeout=TIMEOUT_SECONDS):
    host, port = _address()
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        status, raw = resp.status, resp.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as exc:
        raise OllamaError(
            f"Cannot reach Ollama at {host}:{port} ({exc}).\n"
            "Fix: run 'sudo systemctl start ollama', then 'python check_setup.py'."
        ) from None
    finally:
        conn.close()
    if status != 200:
        hint = ""
        if status == 404 and "not found" in raw:
            hint = "\nFix: download the model first, for example: ollama pull " + str(body.get("model", ""))
        raise OllamaError(f"Ollama answered HTTP {status}: {raw[:200]}{hint}")
    try:
        return json.loads(raw)
    except ValueError:
        raise OllamaError("Ollama answered with something that is not JSON.") from None


def version():
    """The Ollama version as text, for example '0.12.6'."""
    return str(_call("GET", "/api/version", timeout=10).get("version", "0.0.0"))


def installed_models():
    """Names of the models Ollama has on this machine, for example ['all-minilm:latest']."""
    return [m.get("name", "") for m in _call("GET", "/api/tags", timeout=10).get("models", [])]


def normalize(vector):
    """Scale a vector to length 1, so that a dot product equals cosine similarity."""
    length = math.sqrt(sum(x * x for x in vector))
    if length == 0:
        raise OllamaError("The embedding model returned an all-zero vector.")
    return [x / length for x in vector]


def embed(texts, batch_size=16):
    """Return one normalized vector (a list of floats) for each text."""
    if isinstance(texts, str):
        raise TypeError("embed() expects a list of texts")
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = list(texts[start:start + batch_size])
        reply = _call("POST", "/api/embed", {"model": config.EMBED_MODEL, "input": batch}, timeout=300)
        got = reply.get("embeddings")
        if not isinstance(got, list) or len(got) != len(batch):
            raise OllamaError("Ollama /api/embed did not return one embedding per text.")
        for vec in got:
            if len(vec) != config.EMBED_DIMENSIONS:
                raise OllamaError(
                    f"Expected {config.EMBED_DIMENSIONS} numbers per embedding, got {len(vec)}. "
                    f"Is LAB4_EMBED_MODEL set to {config.EMBED_MODEL!r} on purpose?"
                )
            vectors.append(normalize(vec))
    return vectors


def chat(messages, max_tokens=config.MAX_ANSWER_TOKENS, temperature=0):
    """
    Send messages, return (reply_text, usage).
    usage = {"input_tokens": .., "output_tokens": .., "seconds": ..}
    """
    body = {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",
        "options": {
            "temperature": temperature,      # 0 = most repeatable
            "seed": 42,
            "num_ctx": config.NUM_CTX,       # context window: prompt + answer must fit
            "num_predict": max_tokens,       # hard cap on answer tokens
        },
    }
    reply = _call("POST", "/api/chat", body)
    usage = {
        "input_tokens": int(reply.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(reply.get("eval_count", 0) or 0),
        "seconds": round((reply.get("total_duration", 0) or 0) / 1e9, 1),
    }
    return reply.get("message", {}).get("content", ""), usage
