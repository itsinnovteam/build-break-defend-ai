"""
llm.py - a tiny client for the local Ollama API (Python standard library only).

This is the "From chat to API" step: instead of typing into a chat window,
our program sends a JSON request to http://127.0.0.1:11434 and reads JSON back.
Nothing leaves the VM: Ollama and the model run locally, on the CPU.
"""

import http.client
import json
import os

HOST = os.environ.get("LAB3_OLLAMA_HOST", "127.0.0.1")
PORT = int(os.environ.get("LAB3_OLLAMA_PORT", "11434"))
MODEL = os.environ.get("LAB3_MODEL", "llama3.1:8b")
TIMEOUT_SECONDS = 600  # a CPU can need a few minutes for one answer


class LLMError(Exception):
    """Raised when Ollama cannot be reached or answers with an error."""


def _call(method, path, body=None, timeout=TIMEOUT_SECONDS):
    """Send one HTTP request to Ollama and return the decoded JSON reply."""
    conn = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    try:
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json"}
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        raw = resp.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as exc:
        raise LLMError(
            f"Cannot reach Ollama at {HOST}:{PORT} ({exc}).\n"
            "Fix: start it with 'sudo systemctl start ollama', then run "
            "'python check_setup.py'."
        ) from None
    finally:
        conn.close()
    if status != 200:
        raise LLMError(f"Ollama answered HTTP {status}: {raw[:300]}")
    try:
        return json.loads(raw)
    except ValueError:
        raise LLMError("Ollama answered with something that is not JSON.") from None


def version():
    """Return the Ollama version as text, for example '0.6.8'."""
    return _call("GET", "/api/version", timeout=10).get("version", "0.0.0")


def version_tuple(text):
    """'0.6.8' -> (0, 6, 8). Anything unreadable becomes (0, 0, 0)."""
    parts = []
    for piece in str(text).split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def supports_json_schema():
    """Ollama 0.5.0 and newer can force the reply to match a JSON schema."""
    return version_tuple(version()) >= (0, 5, 0)


def installed_models():
    """Names of the models Ollama has on this machine."""
    return [m.get("name", "") for m in _call("GET", "/api/tags", timeout=10).get("models", [])]


def chat(messages, fmt=None, max_tokens=400, temperature=0):
    """
    Send a list of messages and return (reply_text, usage).

    messages : [{"role": "system" | "user" | "assistant", "content": "..."}]
    fmt      : None (free text), "json", or a JSON schema (dict)
    usage    : {"input_tokens": .., "output_tokens": .., "seconds": ..}
    """
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",
        "options": {
            "temperature": temperature,  # 0 = most repeatable answers
            "seed": 42,
            "num_ctx": 4096,  # context window: input + output must fit
            "num_predict": max_tokens,  # hard cap on output tokens
        },
    }
    if fmt is not None:
        body["format"] = fmt
    reply = _call("POST", "/api/chat", body)
    text = reply.get("message", {}).get("content", "")
    usage = {
        "input_tokens": int(reply.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(reply.get("eval_count", 0) or 0),
        "seconds": round((reply.get("total_duration", 0) or 0) / 1e9, 1),
    }
    return text, usage
