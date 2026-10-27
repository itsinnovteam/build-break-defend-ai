"""
ollama_client.py - a tiny client for the local Ollama API (Python standard library only).

Same style as Labs 3 and 4. The one new thing in Module 5 is TOOL CALLING: we send a list
of tool descriptions, and the model may answer with a request to call one of them.

chat(messages, tools) -> (reply_message, usage)
  reply_message = {"role": "assistant", "content": "...", "tool_calls": [ ... ]}
Nothing leaves the VM: Ollama and the model run locally, on the CPU.
"""

import http.client
import json
from urllib.parse import urlparse

import config

TIMEOUT_SECONDS = 600


class OllamaError(Exception):
    """Ollama cannot be reached, or it answered with an error."""


def _address():
    url = urlparse(config.OLLAMA_URL)
    if url.scheme != "http" or not url.hostname:
        raise OllamaError(f"LAB5_OLLAMA_URL must look like http://127.0.0.1:11434 (got {config.OLLAMA_URL!r})")
    return url.hostname, url.port or 11434


def is_local():
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
            hint = "\nFix: download the model first: ollama pull " + str((body or {}).get("model", ""))
        raise OllamaError(f"Ollama answered HTTP {status}: {raw[:200]}{hint}")
    try:
        return json.loads(raw)
    except ValueError:
        raise OllamaError("Ollama answered with something that is not JSON.") from None


def version():
    return str(_call("GET", "/api/version", timeout=10).get("version", "0.0.0"))


def installed_models():
    return [m.get("name", "") for m in _call("GET", "/api/tags", timeout=10).get("models", [])]


def chat(messages, tools=None, max_tokens=400):
    """
    Send messages (and optional tool list) and return (reply_message, usage).
    reply_message may contain "tool_calls": a list of {"function": {"name", "arguments"}}.
    """
    body = {
        "model": config.MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",
        "options": {"temperature": config.TEMPERATURE, "seed": 42,
                    "num_ctx": config.NUM_CTX, "num_predict": max_tokens},
    }
    if tools:
        body["tools"] = tools
    reply = _call("POST", "/api/chat", body)
    message = reply.get("message", {}) or {}
    usage = {
        "input_tokens": int(reply.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(reply.get("eval_count", 0) or 0),
        "seconds": round((reply.get("total_duration", 0) or 0) / 1e9, 1),
    }
    return message, usage
