"""
check_setup.py - run this first. It tells you exactly what is missing.

  python check_setup.py           full check, including one tiny test call to the AI
  python check_setup.py --quick   skip the test call
"""

import sys

failures = 0


def report(ok, label, fix=""):
    global failures
    if ok is True:
        print(f"PASS  {label}")
    elif ok is None:
        print(f"WARN  {label}")
        if fix:
            print(f"      -> {fix}")
    else:
        failures += 1
        print(f"FAIL  {label}")
        if fix:
            print(f"      -> {fix}")


print("Lab 3 setup check\n")

report(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]} (3.9 or newer needed)",
       "Use the Module 0 VM: python3 --version")

in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
report(True if in_venv else None, "virtual environment active" if in_venv else "virtual environment NOT active",
       "Run: source .venv/bin/activate   (see Part 0)")

try:
    import pytest  # noqa: F401
    report(True, "pytest installed (needed in Part 7)")
except ImportError:
    report(None, "pytest not installed (needed in Part 7)",
           "Run: python -m pip install -r requirements.txt")

try:
    import llm
except ImportError:
    report(False, "llm.py not found", "Run this command from inside the lab3 folder: cd ~/lab3")
    sys.exit(1)

try:
    ver = llm.version()
    report(True, f"Ollama is running at {llm.HOST}:{llm.PORT} (version {ver})")
    if llm.version_tuple(ver) >= (0, 5, 0):
        report(True, "Ollama supports JSON-schema structured output (0.5.0 or newer)")
    else:
        report(None, f"Ollama {ver} is older than 0.5.0: no JSON schema support",
               "The lab still works (it falls back to plain JSON mode). "
               "Ask your admin to update Ollama if possible.")
    models = llm.installed_models()
    found = llm.MODEL in models or (llm.MODEL + ":latest") in models
    report(found, f"model {llm.MODEL} is installed",
           f"Run: ollama pull {llm.MODEL}   (installed: {', '.join(models) or 'none'})")
except llm.LLMError as exc:
    report(False, "Ollama is not reachable", str(exc).replace("\n", " "))
    found = False

if found and "--quick" not in sys.argv:
    print("\nTest call to the AI (the first call loads the model: 10-90 s on a CPU)...")
    try:
        text, usage = llm.chat([{"role": "user", "content": "Reply with the single word: ready"}],
                               max_tokens=5)
        report(True, f"AI answered {text.strip()[:30]!r} in {usage['seconds']} s")
    except llm.LLMError as exc:
        report(False, "test call failed", str(exc).replace("\n", " "))

print()
if failures:
    print(f"{failures} problem(s) found. Fix the FAIL lines above, then run this again.")
    sys.exit(1)
print("All required checks passed. You are ready for Lab 3.")
