"""
Step 2 - The system prompt is your behaviour config.

Sends the SAME alert twice:
  A) no system prompt, alert pasted as-is
  B) system prompt from prompts/system_rules.txt, alert wrapped in <alert> tags
Then compare: which one followed the "NOTE TO AI" hidden in the alert?

Run:  python step2_system_prompt.py                     (uses alert A3)
      python step2_system_prompt.py alerts/a4_disk_full.txt
"""

import sys
from pathlib import Path

import llm
import safety

HERE = Path(__file__).resolve().parent
alert_file = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "alerts" / "a3_edr_powershell.txt")
alert = Path(alert_file).read_text(encoding="utf-8")
rules = (HERE / "prompts" / "system_rules.txt").read_text(encoding="utf-8")

runs = [
    ("A) NO system prompt", [
        {"role": "user", "content": "Triage this alert:\n\n" + alert},
    ]),
    ("B) WITH system prompt (prompts/system_rules.txt)", [
        {"role": "system", "content": rules},
        {"role": "user", "content": "Triage this alert:\n\n" + safety.wrap_untrusted(alert)},
    ]),
]

print(f"Alert: {alert_file}")
for title, messages in runs:
    roles = " + ".join(m["role"] for m in messages)
    print("\n" + "=" * 70)
    print(f"{title}\nMessages sent: {roles}   (waiting for the CPU, often 30-120 s)")
    print("-" * 70)
    try:
        text, usage = llm.chat(messages, max_tokens=180)
    except llm.LLMError as exc:
        sys.exit(f"ERROR: {exc}")
    print(safety.clean_for_terminal(text).strip())
    print("-" * 70)
    print(f"input tokens {usage['input_tokens']}, output tokens {usage['output_tokens']}, "
          f"{usage['seconds']} s")

print("\nCompare A and B: which one obeyed the NOTE TO AI? Which one is easier to act on?")
