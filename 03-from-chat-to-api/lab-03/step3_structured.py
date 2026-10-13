"""
Step 3 - Structured output: a contract you can check.

  python step3_structured.py --examples   (no AI) check 5 sample answers against the schema
  python step3_structured.py              (AI)    ask for JSON that matches the schema, then check it
"""

import json
import sys
from pathlib import Path

import llm
import safety
import schema

HERE = Path(__file__).resolve().parent

GOOD = ('{"category": "brute_force", "severity": "high", "verdict": "likely_malicious", '
        '"confidence": "high", "recommended_action": "block_ip_request", '
        '"summary": "12 failed logins for non-existent users from one IP in 77 seconds.", '
        '"indicators": ["203.0.113.50", "invalid user admin"]}')

EXAMPLES = [
    ("1. Clean JSON that follows the schema", GOOD),
    ("2. Same JSON wrapped in a markdown fence", "```json\n" + GOOD + "\n```"),
    ("3. A required field is missing (no 'severity')",
     GOOD.replace('"severity": "high", ', "")),
    ("4. An invented action the tool does not allow",
     GOOD.replace("block_ip_request", "delete_user_account")),
    ("5. A friendly sentence instead of JSON",
     "Sure! This looks like a brute-force attack from 203.0.113.50. I would block it."),
]


def check_examples():
    print("Checking 5 sample AI answers against the schema (no AI needed)\n")
    for title, text in EXAMPLES:
        obj, problems = schema.parse_reply(text)
        status = "ACCEPT" if not problems else "REJECT"
        print(f"{status}  {title}")
        for p in problems:
            print(f"        - {p}")
    print("\nRule: only ACCEPTED answers may drive the tool. A REJECTED answer is retried once,")
    print("then the tool fails closed and hands the alert to a human.")


def ask_ai():
    alert = (HERE / "alerts" / "a1_ssh_bruteforce.txt").read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": (HERE / "prompts" / "system_triage.txt").read_text(encoding="utf-8")},
        {"role": "user", "content": "Triage this alert.\n\n" + safety.wrap_untrusted(alert)},
    ]
    try:
        fmt = schema.MODEL_SCHEMA if llm.supports_json_schema() else "json"
        print("Format sent to Ollama:", "the JSON schema (model is forced to follow it)"
              if isinstance(fmt, dict) else "'json' (older Ollama: JSON, but no schema)")
        print("Waiting for the CPU (often 30-120 s)...\n")
        text, usage = llm.chat(messages, fmt=fmt, max_tokens=400)
    except llm.LLMError as exc:
        sys.exit(f"ERROR: {exc}")
    print("RAW REPLY FROM THE MODEL:")
    print(safety.clean_for_terminal(text).strip())
    obj, problems = schema.parse_reply(text)
    print("\nVALIDATION:", "ACCEPT - matches the schema" if not problems else "REJECT")
    for p in problems:
        print("  -", p)
    if obj is not None and not problems:
        print("\nNow code can use it safely, for example:")
        print("  result['recommended_action'] =", json.dumps(obj["recommended_action"]))
        print("  result['indicators'] =", json.dumps(obj["indicators"]))
    print(f"\ninput tokens {usage['input_tokens']}, output tokens {usage['output_tokens']}, "
          f"{usage['seconds']} s")


if __name__ == "__main__":
    if "--examples" in sys.argv:
        check_examples()
    else:
        ask_ai()
