"""Tiny Ollama client using only the Python standard library (no pip installs).

Two functions are all the labs need:
    chat(messages)   -> the model's reply as text
    embed(texts)     -> one embedding (list of floats) per text
"""
import json
import urllib.error
import urllib.request

import config


def _post(path, payload):
    """POST JSON to Ollama and return the parsed JSON reply."""
    req = urllib.request.Request(
        config.OLLAMA_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(messages, temperature=0.0):
    """Send a list of {"role", "content"} messages and return the reply text.

    temperature=0 makes answers repeatable, which helps when comparing runs.
    """
    reply = _post("/api/chat", {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    })
    return reply["message"]["content"]


def embed(texts):
    """Return a list of embeddings, one per input text."""
    try:
        reply = _post("/api/embed", {"model": config.EMBED_MODEL, "input": texts})
        return reply["embeddings"]
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        # Older Ollama versions only have /api/embeddings (one text per call).
        return [
            _post("/api/embeddings", {"model": config.EMBED_MODEL, "prompt": t})["embedding"]
            for t in texts
        ]
