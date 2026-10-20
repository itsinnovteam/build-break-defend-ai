"""
safety.py - plain-code safety checks (no AI). Same ideas as Lab 3.

  find_injection()      spot text that tries to give orders to the AI
  defuse_tags()         stop retrieved text from closing our <source> tags
  clean_for_terminal()  remove hidden control codes from AI output before printing

Phrase matching is a best-effort check, not a guarantee. That is why retrieved text is
ALSO always marked as data in the prompt, and why access control never depends on it.
"""

import re

INJECTION_PATTERNS = [
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions|rules)",
    r"disregard (?:the |all |any )?(?:previous |prior |above )?(?:instructions|rules)",
    r"note to (?:the )?(?:ai|assistant|model|llm)",
    r"\byou are now\b",
    r"system prompt",
    r"</?\s*source\b",
]
_INJECTION = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def find_injection(text):
    """Return the suspicious phrases found in the text (empty list = none found)."""
    found = []
    for pattern in _INJECTION:
        match = pattern.search(text)
        if match:
            found.append(match.group(0))
    return found


def defuse_tags(text):
    """'</source>' inside a document becomes harmless text, so data cannot break out of its tag."""
    return re.sub(r"(?i)<\s*(/?)\s*source\b[^>]*>?", r"[\1source-tag-removed]", text)


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_for_terminal(text):
    """Remove terminal escape codes and control characters (keeps tabs and newlines)."""
    return _CONTROL.sub("", _ANSI.sub("", str(text)))
