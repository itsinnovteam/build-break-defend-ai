"""
check_setup.py - Phase 1: check everything Lab 5 needs and say exactly how to fix what is missing.

Run:  python check_setup.py
"""

import importlib.util
import json
import sys

import config


def main():
    print("Lab 5 setup check\n")
    failed = []

    def ok(m):
        print(f"PASS  {m}")

    def fail(m, fix):
        failed.append(m)
        print(f"FAIL  {m}\n      Fix: {fix}")

    if sys.version_info >= (3, 9):
        ok(f"Python {sys.version.split()[0]}")
    else:
        fail(f"Python {sys.version.split()[0]} is too old", "use Python 3.9 or newer")
    if sys.prefix != sys.base_prefix:
        ok("virtual environment is active")
    else:
        fail("virtual environment is not active", "run: source .venv/bin/activate")

    for mod in ("pytest", "bandit"):
        if importlib.util.find_spec(mod):
            ok(f"{mod} installed")
        else:
            fail(f"{mod} is not installed", "python -m pip install -r requirements.txt")

    try:
        import toolkit
        alerts = sorted(json.loads(p.read_text())["alert_id"] for p in config.SCENARIO_DIR.glob("*.json"))
        ok(f"{len(toolkit.tool_names())} tools and {len(alerts)} scenarios ({', '.join(alerts)})")
    except Exception as exc:
        fail(f"lab files: {exc}", "re-copy the lab5 folder from the Module 5 package")

    try:
        import mcp_client
        c = mcp_client.MCPClient()
        try:
            n = len(c.call("tools/list")["tools"])
            ok(f"MCP server answers (exposes {n} read-only tools)")
        finally:
            c.close()
    except Exception as exc:
        fail(f"MCP server: {exc}", "check mcp_server.py is present")

    try:
        import ollama_client
        ok(f"Ollama {ollama_client.version()} is running at {config.OLLAMA_URL}"
           + (" (local)" if ollama_client.is_local() else " (NOT local)"))
        base = config.MODEL if ":" in config.MODEL else config.MODEL + ":latest"
        if base in ollama_client.installed_models() or config.MODEL in ollama_client.installed_models():
            ok(f"model {config.MODEL} is installed")
        else:
            fail(f"model {config.MODEL} is not installed", f"ollama pull {config.MODEL}")
        if not failed:
            msg, _ = ollama_client.chat(
                [{"role": "user", "content": "Reply with the single word: ready"}], max_tokens=5)
            ok(f"model answered {msg.get('content', '').strip()[:20]!r} "
               "(the first call loads the model; later calls are faster)")
    except Exception as exc:
        fail(f"Ollama: {exc}", "run: sudo systemctl start ollama")

    print()
    if failed:
        print(f"{len(failed)} check(s) failed. Fix them in order, then run: python check_setup.py")
        return 1
    print("All required checks passed. You are ready for Lab 5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
