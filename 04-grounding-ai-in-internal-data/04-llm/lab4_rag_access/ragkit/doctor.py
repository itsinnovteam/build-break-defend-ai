"""Check the lab environment:  python3 -m ragkit.doctor"""
from __future__ import annotations

import json
import sys
import urllib.request

from . import config
from .embeddings import ollama_has_model


def check(label: str, ok: bool, hint: str = "") -> bool:
    print("  [{}] {}{}".format("OK" if ok else "!!", label, "" if ok or not hint else "\n       -> " + hint))
    return ok


def main() -> int:
    print("Lab 4 environment check\n")
    good = True
    good &= check("Python {}.{} (need 3.9+)".format(*sys.version_info[:2]), sys.version_info >= (3, 9))
    docs = list(config.DOCS_DIR.glob("*.md"))
    good &= check("{} documents in data/docs".format(len(docs)), len(docs) >= 8, "lab files incomplete - copy the folder again")
    good &= check("users.json present", config.USERS_FILE.exists())

    try:
        with urllib.request.urlopen(config.OLLAMA_URL + "/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.loads(resp.read().decode())["models"]]
        reachable = True
    except Exception:
        names, reachable = [], False
    good &= check("Ollama reachable at " + config.OLLAMA_URL, reachable, "start it: sudo systemctl start ollama")
    if reachable:
        good &= check("chat model " + config.CHAT_MODEL, ollama_has_model(config.CHAT_MODEL),
                      "ollama pull " + config.CHAT_MODEL)
        has_embed = ollama_has_model(config.EMBED_MODEL)
        check("embedding model {} (optional)".format(config.EMBED_MODEL), has_embed,
              "optional: ollama pull {}  (otherwise the lexical embedder is used)".format(config.EMBED_MODEL))

    check("index built", config.INDEX_FILE.exists(), "python3 -m ragkit.ingest")
    print("\nPolicy:")
    for k, v in config.load_policy().items():
        print("  [{}] {}".format("ON " if v else "off", k))
    print("\nReady." if good else "\nFix the items marked !! before starting.")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
