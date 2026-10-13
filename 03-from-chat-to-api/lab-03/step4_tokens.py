"""
Step 4 - Tokens, context window and cost.

  python step4_tokens.py --offline   (no AI) estimate tokens and cost with simple maths
  python step4_tokens.py             (AI)    also measure real token counts from Ollama
"""

import json
import sys
from pathlib import Path

import llm
import safety

HERE = Path(__file__).resolve().parent
PRICES = json.loads((HERE / "prices.example.json").read_text(encoding="utf-8"))
CLOUD = PRICES["example_cloud_model"]
SYSTEM = (HERE / "prompts" / "system_triage.txt").read_text(encoding="utf-8")

INPUTS = [
    ("Short: alerts/a1_ssh_bruteforce.txt", HERE / "alerts" / "a1_ssh_bruteforce.txt"),
    ("Long:  sample_auth.log (whole file)", HERE / "sample_auth.log"),
]
EXPECTED_OUTPUT_TOKENS = 150  # a typical triage answer
ALERTS_PER_DAY = 1000
CONTEXT_WINDOW = 4096


def estimate_tokens(text):
    """Rule of thumb for English and logs: about 4 characters per token."""
    return round(len(text) / 4)


def cost(inp, out):
    return (inp * CLOUD["input_per_million_tokens"] + out * CLOUD["output_per_million_tokens"]) / 1_000_000


def offline():
    print("ESTIMATE (rule of thumb: 1 token is about 4 characters)")
    print(f"Example cloud prices from prices.example.json: input ${CLOUD['input_per_million_tokens']:.2f}"
          f" and output ${CLOUD['output_per_million_tokens']:.2f} per 1 million tokens\n")
    print(f"{'Input':38} {'chars':>6} {'~tokens':>8} {'cost/alert':>11} {'per month*':>11} {'window':>7}")
    for title, path in INPUTS:
        text = SYSTEM + path.read_text(encoding="utf-8")
        tokens = estimate_tokens(text)
        per_alert = cost(tokens, EXPECTED_OUTPUT_TOKENS)
        used = (tokens + EXPECTED_OUTPUT_TOKENS) / CONTEXT_WINDOW
        print(f"{title:38} {len(text):>6} {tokens:>8} {'$%.5f' % per_alert:>11} "
              f"{'$%.2f' % (per_alert * ALERTS_PER_DAY * 30):>11} {used:>6.0%}")
    print(f"\n* {ALERTS_PER_DAY} alerts per day for 30 days, {EXPECTED_OUTPUT_TOKENS} output tokens each,"
          " system prompt included.")
    print(f"window = share of the {CONTEXT_WINDOW}-token context window used (input + answer).")
    print("Output tokens cost more than input tokens, so short answers save money.")


def measured():
    print("\nMEASURED by Ollama (real token counts for llama3.1:8b)")
    for title, path in INPUTS:
        text = path.read_text(encoding="utf-8")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": "Triage this alert.\n\n" + safety.wrap_untrusted(text)}]
        print(f"\n{title}: waiting for the CPU...")
        try:
            _, usage = llm.chat(messages, fmt="json", max_tokens=200)
        except llm.LLMError as exc:
            sys.exit(f"ERROR: {exc}")
        speed = usage["output_tokens"] / usage["seconds"] if usage["seconds"] else 0
        print(f"  input tokens  : {usage['input_tokens']}  (estimate was {estimate_tokens(SYSTEM + text)})")
        print(f"  output tokens : {usage['output_tokens']}")
        print(f"  time          : {usage['seconds']} s  (about {speed:.1f} output tokens per second on this CPU)")
        print(f"  example cloud cost for this call: ${cost(usage['input_tokens'], usage['output_tokens']):.5f}")
    print("\nNote: if you run this twice, the input count can be lower the second time,")
    print("because Ollama reuses work it has cached for an identical prompt start.")


if __name__ == "__main__":
    offline()
    if "--offline" not in sys.argv:
        measured()
