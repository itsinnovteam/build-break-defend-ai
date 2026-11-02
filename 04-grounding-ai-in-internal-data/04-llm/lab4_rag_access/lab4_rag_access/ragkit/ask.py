"""Ask SOC Copilot a question.

    export LAB4_TOKEN=tok-carla-d07a          # "log in" as Carla
    python3 -m ragkit.ask "How do I unlock an account?"
    python3 -m ragkit.ask --show-context --no-llm "..."   # retrieval only, fast
    python3 -m ragkit.ask --groups soc-leads "..."        # claim extra groups (Part B)
    python3 -m ragkit.ask --trace --no-llm "..."          # show every query-pipeline stage
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time

from . import config
from .assistant import Assistant, Result
from .embeddings import preview
from .llm import LLMError


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask SOC Copilot (Lab 4)")
    parser.add_argument("question")
    parser.add_argument("--token", default=os.environ.get("LAB4_TOKEN"),
                        help="session token (default: $LAB4_TOKEN)")
    parser.add_argument("--groups", help="comma-separated groups the CLIENT claims (simulates a request header)")
    parser.add_argument("--no-llm", action="store_true", help="skip the LLM: show retrieval only (fast)")
    parser.add_argument("--show-context", action="store_true", help="print exactly what the model was given")
    parser.add_argument("--trace", action="store_true", help="walk through every stage of the query pipeline")
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

    if args.trace:
        print_trace(r, args.no_llm)
        return

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


def stage(n: int, name: str) -> None:
    print("\n[{}] {}\n{}".format(n, name.upper(), "-" * (len(name) + 4)))


def print_trace(r: Result, no_llm: bool) -> None:
    """Print the query pipeline stage by stage, matching the course diagram."""
    if r.cached:
        print("Cache HIT: stages 2-6 were skipped. The stored answer was returned as-is.\n")
        print("ANSWER:\n" + r.answer)
        return
    t = r.trace
    stage(1, "User Question")
    print(r.question)
    stage(2, "Question Embedding")
    print(preview(t["question_embedding"]))
    stage(3, "Retrieve Relevant Chunks (vector DB search, top-{})".format(len(t["hits"])))
    for cid, score in t["hits"]:
        print("  score {:.3f}  {}".format(score, cid))
    stage(4, "Context")
    for i, c in enumerate(r.context, 1):
        print("  [{}] {} - {}  (label: {}; allowed: {})".format(
            i, c["title"], c["section"], c["classification"], ", ".join(c["allowed_groups"])))
    stage(5, "Prompt + Context (what the LLM receives)")
    for m in t["messages"]:
        print(">>> {} message:".format(m["role"]))
        print(textwrap.indent(m["content"], "    "))
    stage(6, "LLM")
    print("skipped (--no-llm)" if no_llm else "Ollama model: {}".format(config.CHAT_MODEL))
    stage(7, "Grounded Response")
    print(r.answer)


if __name__ == "__main__":
    main()
