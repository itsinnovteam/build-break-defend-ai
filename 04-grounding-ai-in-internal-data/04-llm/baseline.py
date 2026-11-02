"""Lab 4.1 - Baseline: ask the model WITHOUT any internal data.

Run:
    python3 baseline.py
    python3 baseline.py "How should I investigate this alert? Multiple failed logins, then a successful login from an unusual location."
"""
import sys

import ollama_client

DEFAULT_QUESTION = (
    "Our SIEM raised this alert: multiple failed logins, then a successful "
    "login from an unusual location. How should I investigate this alert, "
    "how severe is it, and who do I escalate to?"
)


def main():
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    print("QUESTION:\n" + question + "\n")
    print("Asking the model with NO internal data (this can take a minute on CPU)...\n")
    answer = ollama_client.chat([
        {"role": "system", "content": "You are an assistant for a Security Operations Center analyst."},
        {"role": "user", "content": question},
    ])
    print("ANSWER:\n" + answer)


if __name__ == "__main__":
    main()
