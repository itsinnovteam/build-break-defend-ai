"""Ask SOC Copilot a question.

    export LAB4_TOKEN=tok-carla-d07a          # "log in" as Carla
    python3 -m ragkit.ask "How do I unlock an account?"
    python3 -m ragkit.ask --show-context --no-llm "..."   # retrieval only, fast
    python3 -m ragkit.ask --groups soc-leads "..."        # claim extra groups (Part B)
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time

from . import config
from .assistant import Assistant
from .llm import LLMError


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask SOC Copilot (Lab 4)")
    parser.add_argument("question")
    parser.add_argument("--token", default=os.environ.get("LAB4_TOKEN"),
                        help="session token (default: $LAB4_TOKEN)")
    parser.add_argument("--groups", help="comma-separated groups the CLIENT claims (simulates a request header)")
    parser.add_argument("--no-llm", action="store_true", help="skip the LLM: show retrieval only (fast)")
    parser.add_argument("--show-context", action="store_true", help="print exactly what the model was given")
    args = parser.parse_args()

    policy = config.load_policy()
    claimed = [g.strip() for g in args.groups.split(",")] if args.groups else None
    bot = Assistant(policy, use_llm=not args.no_llm)

    start = time.time()
    try:
        r = bot.ask(args.token, args.question, claimed_groups=claimed)
    except LLMError as err:
        sys.exit("[error] {}".format(err))

    print("User   : {} ({}) - identity provider groups: {}".format(r.user.name, r.user.role, ", ".join(r.user.groups)))
    if claimed:
        print("Claimed: {}".format(", ".join(claimed)))
    print("Used   : {}".format(", ".join(r.groups)))
    print("Cache  : {}".format("HIT (answer served from cache, no retrieval)" if r.cached else "miss"))
    print("Time   : {:.1f}s\n".format(time.time() - start))

    if args.show_context:
        print("=" * 30 + " CONTEXT SENT TO THE MODEL " + "=" * 30)
        for i, c in enumerate(r.context, 1):
            flag = "  <-- RESTRICTED" if c["classification"] == "restricted" else ""
            print("[{}] {} | {} | {} | allowed: {}{}".format(
                i, c["id"], c["section"], c["classification"], ", ".join(c["allowed_groups"]), flag))
            print(textwrap.indent(textwrap.fill(c["text"], 96), "    "))
        print("=" * 87 + "\n")

    print("ANSWER:\n" + r.answer)
    print("\nSOURCES:")
    for i, c in enumerate(r.context, 1):
        print("  [{}] {} - {} ({})".format(i, c["title"], c["section"], c["classification"]))


if __name__ == "__main__":
    main()
