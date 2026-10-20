"""
check_setup.py - Phase 1: check everything Lab 4 needs, and say exactly how to fix what is missing.

Run:  python check_setup.py
"""

import importlib.util
import sqlite3
import sys
import time

import config

FAILED = []


def ok(message):
    print(f"PASS  {message}")


def fail(message, fix):
    FAILED.append(message)
    print(f"FAIL  {message}\n      Fix: {fix}")


def main():
    print("Lab 4 setup check\n")
    if sys.version_info >= (3, 9):
        ok(f"Python {sys.version.split()[0]}")
    else:
        fail(f"Python {sys.version.split()[0]} is too old", "use Python 3.9 or newer (Oracle Linux 9: python3)")
    if sys.prefix != sys.base_prefix:
        ok("virtual environment is active")
    else:
        fail("virtual environment is not active", "run: source .venv/bin/activate")
    ok(f"SQLite {sqlite3.sqlite_version} (built into Python - used as the vector store)")

    for module, fix in (("pytest", "python -m pip install -r requirements.txt"),
                        ("bandit", "python -m pip install -r requirements.txt")):
        if importlib.util.find_spec(module):
            ok(f"{module} installed")
        else:
            fail(f"{module} is not installed", fix)

    try:
        import identity
        import pipeline
        docs = pipeline.load_documents()
        users = identity.load_directory()
        ok(f"{len(docs)} documents in kb/ with valid metadata, {len(users)} users in config/directory.json")
    except Exception as exc:          # show any problem with the lab files in plain words
        fail(f"lab files: {exc}", "re-copy the lab4 folder from the Module 4 package")

    try:
        import ollama_client
        version = ollama_client.version()
        ok(f"Ollama {version} is running at {config.OLLAMA_URL}"
           + (" (local)" if ollama_client.is_local() else " (NOT local)"))
        models = ollama_client.installed_models()
        for wanted in (config.CHAT_MODEL, config.EMBED_MODEL):
            base = wanted if ":" in wanted else wanted + ":latest"
            if base in models or wanted in models:
                ok(f"model {wanted} is installed")
            else:
                fail(f"model {wanted} is not installed", f"run: ollama pull {wanted}")
        if not FAILED:
            vector = ollama_client.embed(["test"])[0]
            ok(f"embedding model answered: {len(vector)} numbers per text")
            started = time.time()
            text, _ = ollama_client.chat([{"role": "user", "content": "Reply with the single word: ready"}],
                                         max_tokens=5)
            ok(f"chat model answered {text.strip()[:20]!r} in {time.time() - started:.0f} s "
               "(the first call loads the model; later calls are faster)")
    except Exception as exc:          # Ollama problems are explained by ollama_client
        fail(f"Ollama: {exc}", "run: sudo systemctl start ollama   (then run this check again)")

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed. Fix them in order, then run: python check_setup.py")
        return 1
    print("All required checks passed. You are ready for Lab 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
