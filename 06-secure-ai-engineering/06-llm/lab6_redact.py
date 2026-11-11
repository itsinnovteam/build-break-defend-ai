#!/usr/bin/env python3
"""Lab 6 - redact secrets before text reaches the model.

Rule 2 from Module 6 ("redact at the tool boundary"), made runnable.

  python3 lab6_redact.py                      # redact case NW-4480 from Lab 5's soc.json
  python3 lab6_redact.py --case NW-4480 --out ~/lab6/evidence/case-notes-redacted.txt
  python3 lab6_redact.py --mask-email         # also mask e-mail addresses
  echo "token: abc123" | python3 lab6_redact.py --stdin
  python3 lab6_redact.py --selftest           # prove the redactor works, no Lab 5 files needed

To use it inside an agent, wrap the tool, not the prompt:

  from lab6_redact import redact_text
  def get_case_notes(case_id):
      return redact_text(base.get_case_notes(case_id))

Standard library only. Works on Python 3.9+.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / "05-llm" / "lab5_hijack_data" / "soc.json"

# Patterns for values that must never reach a model (data class: Restricted).
# Order matters: specific patterns first, the generic "key: value" rule last.
PATTERNS = [
    ("TOKEN", re.compile(r"\bnw_[A-Za-z0-9_]{8,}")),            # Northwind lab tokens
    ("PRIVATE_KEY", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("BEARER", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
]
KEY_VALUE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)\b(\s*[:=]\s*)([^\s,;]+)")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
SENSITIVE_KEYS = re.compile(r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?key|token|credential)")


def redact(text, mask_email=False):
    """Return (redacted_text, {label: count})."""
    counts = {}

    def bump(label):
        counts[label] = counts.get(label, 0) + 1

    for label, pattern in PATTERNS:
        def sub(_m, label=label):
            bump(label)
            return "[REDACTED:%s]" % label
        text = pattern.sub(sub, text)

    def kv(m):
        if m.group(3).startswith("[REDACTED"):
            return m.group(0)
        bump("SECRET")
        return "%s%s[REDACTED:SECRET]" % (m.group(1), m.group(2))
    text = KEY_VALUE.sub(kv, text)

    if mask_email:
        def em(_m):
            bump("EMAIL")
            return "[EMAIL]"
        text = EMAIL.sub(em, text)
    return text, counts


def redact_text(text, mask_email=False):
    """Drop-in wrapper for tool results: returns only the redacted string."""
    return redact(text, mask_email)[0]


def redact_obj(obj, counts, mask_email=False, key=None):
    """Redact every string in a JSON structure. A sensitive key hides its whole value."""
    if isinstance(obj, dict):
        return {k: redact_obj(v, counts, mask_email, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v, counts, mask_email, key) for v in obj]
    if isinstance(obj, str):
        if key is not None and SENSITIVE_KEYS.search(str(key)):
            counts["SECRET_FIELD"] = counts.get("SECRET_FIELD", 0) + 1
            return "[REDACTED:SECRET_FIELD]"
        new, c = redact(obj, mask_email)
        for k, v in c.items():
            counts[k] = counts.get(k, 0) + v
        return new
    return obj


def find_case(obj, case_id):
    """Find the parts of a JSON document that belong to case_id.

    Matches a key equal to case_id, or a dict that has a value equal to case_id.
    Parts whose path mentions 'note' are preferred (the case notes themselves).
    """
    hits = []

    def walk(o, path):
        if isinstance(o, dict):
            if any(isinstance(v, str) and v == case_id for v in o.values()):
                hits.append((path, o))
                return
            for k, v in o.items():
                p = path + [str(k)]
                if str(k) == case_id:
                    hits.append((p, v))
                else:
                    walk(v, p)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + [str(i)])

    walk(obj, [])
    notes = [h for h in hits if any("note" in part.lower() for part in h[0])]
    return notes or hits


def render(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False)


def selftest():
    sample = {
        "case_notes": {
            "NW-4480": ("Case NW-4480 (internal). Analyst: k.lim. SOAR API token for "
                        "re-scans: nw_FAKE_TOKEN_9f2c41d7e0 (lab value, not real). "
                        "password=Winter2026! Contact soc-lead@northwind.example"),
        },
        "integrations": {"soar": {"api_key": "abc123"}},
    }
    counts = {}
    out = render(redact_obj(sample, counts, mask_email=True))
    checks = [
        ("lab token removed", "nw_FAKE_TOKEN" not in out),
        ("password removed", "Winter2026" not in out),
        ("api_key field removed", "abc123" not in out),
        ("e-mail masked", "soc-lead@" not in out),
        ("analyst context kept", "Analyst: k.lim" in out),
        ("redaction marked", "[REDACTED:TOKEN]" in out),
    ]
    ok = all(passed for _, passed in checks)
    for name, passed in checks:
        print("  %-24s %s" % (name, "PASS" if passed else "FAIL"))
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Redact secrets before text reaches a model (Lab 6).")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="Lab 5 soc.json (default: %(default)s)")
    ap.add_argument("--case", default="NW-4480", help="case id to extract (default: %(default)s)")
    ap.add_argument("--out", help="write the redacted evidence file here")
    ap.add_argument("--mask-email", action="store_true", help="also replace e-mail addresses with [EMAIL]")
    ap.add_argument("--stdin", action="store_true", help="redact text read from standard input")
    ap.add_argument("--selftest", action="store_true", help="run built-in checks and exit")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    counts = {}
    if args.stdin:
        body, counts = redact(sys.stdin.read(), args.mask_email)
        source = "stdin"
    else:
        path = Path(args.data).expanduser()
        if not path.is_file():
            print("ERROR: %s not found. Use --data to point at lab5_hijack_data/soc.json" % path,
                  file=sys.stderr)
            return 2
        doc = json.loads(path.read_text(encoding="utf-8"))
        hits = find_case(doc, args.case)
        if not hits:
            print("WARNING: case %s not found; redacting the whole file instead." % args.case,
                  file=sys.stderr)
            hits = [([], doc)]
        parts = []
        for p, value in hits:
            red = redact_obj(value, counts, args.mask_email)
            parts.append("## %s\n%s" % ("/".join(p) or "(whole file)", render(red)))
        body = "\n\n".join(parts)
        source = "%s, case %s" % (path, args.case)

    summary = ", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "none found"
    report = ("# Lab 6 redaction evidence\n# source: %s\n# redactions: %s\n\n%s\n"
              % (source, summary, body))
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print("wrote %s (redactions: %s)" % (out, summary))
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
