"""Minimal client for the local Ollama chat API (standard library only)."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Dict, List

from . import config


class LLMError(RuntimeError):
    pass


def chat(messages: List[Dict[str, str]], model: str = config.CHAT_MODEL) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": config.NUM_CTX,
            "num_predict": config.NUM_PREDICT,
        },
    }
    req = urllib.request.Request(
        config.OLLAMA_URL + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as err:
        raise LLMError(
            "Cannot reach Ollama at {} ({}). Is it running? Try: systemctl status ollama".format(
                config.OLLAMA_URL, err)
        )
    except (socket.timeout, TimeoutError):
        raise LLMError("Ollama took longer than {}s. CPU-only models are slow; "
                       "raise LAB4_LLM_TIMEOUT or use --no-llm.".format(config.LLM_TIMEOUT))
    return data.get("message", {}).get("content", "").strip()
