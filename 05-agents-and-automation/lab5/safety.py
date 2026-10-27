"""
safety.py - plain-code safety checks (no AI). Carried on from Labs 2, 3 and 4.

  find_injection(text)   spot text that tries to give orders to the agent
  wrap_observation(text) mark a tool result as DATA before it goes back to the model
  clean_for_terminal()   remove hidden control codes before printing

Phrase matching is best-effort, never a guarantee. The real defence is that OUR CODE
decides which tools run - the model's reply is only a request (agent.py).
"""

import re

INJECTION_PATTERNS = [
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions|rules|steps)",
    r"disregard (?:the |all |any )?(?:previous |prior |above )?(?:instructions|rules)",
    r"note (?:for|to) (?:the )?(?:ai|assistant|analyst assistant|agent|model|llm)",
    r"\byou are now\b",
    r"\bsystem\s*:",
    r"new instructions?\b",
    r"instead(?:,| of).{0,40}\b(?:call|run|use|email|send|disable|delete|block)\b",
]
_INJECTION = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def find_injection(text):
    """Return the suspicious phrases found in the text (empty list = none found)."""
    found = []
    for pattern in _INJECTION:
        match = pattern.search(str(text))
        if match:
            found.append(match.group(0).strip())
    return found


def wrap_observation(text):
    """A tool result is DATA, not instructions. Defuse any tag that tries to break out."""
    text = re.sub(r"(?i)<\s*/?\s*(observation|tool_result|system)\b[^>]*>?", "[tag-removed]", str(text))
    return f"<observation>\n{text}\n</observation>"


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_for_terminal(text):
    """Remove terminal escape codes and control characters (keeps tabs and newlines)."""
    return _CONTROL.sub("", _ANSI.sub("", str(text)))
