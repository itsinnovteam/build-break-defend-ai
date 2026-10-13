"""
safety.py - the security layer of the triage tool.

Everything here is plain code (no AI), so it behaves the same every time:
  redact()            remove secrets and e-mail addresses BEFORE anything is sent
  find_injection()    spot text that tries to give orders to the AI
  wrap_untrusted()    put the alert inside <alert> tags it cannot break out of
  clean_for_terminal  remove hidden control codes from AI output before printing
"""

import re

# ---- 1. Redaction: secrets never leave this program -------------------------
# Each rule: (name, pattern, replacement). Order matters: specific rules first.
REDACTION_RULES = [
    ("private key block",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED-PRIVATE-KEY]"),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED-AWS-KEY]"),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer [REDACTED-TOKEN]"),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"),
     "[REDACTED-JWT]"),
    ("password/secret/token value",
     re.compile(r"(?i)\b([A-Z0-9_]*(?:PASSWORD|PASSWD|PWD|SECRET|TOKEN|API_?KEY|ACCESS_?KEY)[A-Z0-9_]*)"
                r"(\s*[:=]\s*)(?!\[REDACTED)(\"[^\"]*\"|'[^']*'|\S+)"),
     r"\1\2[REDACTED]"),
    ("e-mail address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
]


def redact(text):
    """Return (clean_text, list_of_rule_names_that_matched_once_per_match)."""
    hits = []
    for name, pattern, replacement in REDACTION_RULES:
        text, count = pattern.subn(replacement, text)
        hits.extend([name] * count)
    return text, hits


# ---- 2. Prompt-injection detection -------------------------------------------
INJECTION_PATTERNS = [
    r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions|rules)",
    r"disregard (?:the |all |any )?(?:previous |prior |above )?(?:instructions|rules)",
    r"note to (?:the )?(?:ai|assistant|model|llm)",
    r"\byou are now\b",
    r"system prompt",
    r"mark (?:this |it |the alert )?(?:as )?(?:a )?(?:false positive|benign|safe|resolved)",
    r"do not (?:escalate|alert|report)",
    r"</?\s*alert\b",
]
_INJECTION = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def find_injection(text):
    """Return the suspicious phrases found in the text (empty list = none)."""
    found = []
    for pattern in _INJECTION:
        match = pattern.search(text)
        if match:
            found.append(match.group(0))
    return found


# ---- 3. Keep untrusted data inside its tags ---------------------------------
def wrap_untrusted(text):
    """Wrap the alert in <alert> tags. Any tag inside the data is defused first."""
    defused = re.sub(r"(?i)<\s*(/?)\s*alert\s*>?", r"[\1alert-tag-removed]", text)
    return "<alert>\n" + defused.strip() + "\n</alert>"


# ---- 4. Clean AI output before it reaches the terminal ------------------------
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_for_terminal(text):
    """Remove terminal escape codes and control characters (keeps tabs and newlines)."""
    return _CONTROL.sub("", _ANSI.sub("", str(text)))
