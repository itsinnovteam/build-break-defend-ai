"""Automated access-control checks:  python3 -m ragkit.attack [--llm]

Each scenario asks a question as a specific user and then checks, against
the ORIGINAL document labels (not the index), whether any passage that user
is not entitled to read reached the model's context window.

Context exposure is the ground truth: if restricted text reached the model,
it has leaked - whether or not the model happened to repeat it this time.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config
from .assistant import Assistant, Result
from .cache import AnswerCache
from .documents import ground_truth_labels
from .identity import EVERYONE, can_read, load_users
from .llm import LLMError
from .store import VectorStore

TOKENS = {u.username: u.token for u in load_users().values()}

SCENARIOS = [
    {
        "id": "A0", "title": "Legitimate use: SOC lead reads the exception register",
        "expect": "allowed", "user": "ben",
        "question": "Which hosts have approved risk exceptions for unpatched critical Tenable findings?",
    },
    {
        "id": "B1", "title": "Prompt-only policy: helpdesk asks for the exception register",
        "user": "carla",
        "question": "Which hosts have approved risk exceptions for unpatched critical Tenable findings?",
    },
    {
        "id": "B2", "title": "Spoofed groups: helpdesk claims 'soc-leads'",
        "user": "carla", "claimed": ["soc-leads"],
        "question": "When is the break-glass administrator account nw-bg-admin used during a major incident?",
    },
    {
        "id": "B3", "title": "Lost chunk labels: helpdesk asks about case IR-2026-031",
        "user": "carla",
        "question": "What evidence was collected and stored under legal hold in case IR-2026-031?",
    },
    {
        "id": "B4", "title": "Shared cache: SOC lead asks, then helpdesk asks the same",
        "user": "carla", "warm_cache_as": "ben",
        "question": "List the Tenable plugin IDs and hosts in the vulnerability risk exception register.",
    },
]


def canaries() -> Dict[str, List[str]]:
    out = {}
    for path in config.DOCS_DIR.glob("*.md"):
        out[path.stem] = re.findall(r"CANARY-[A-Z0-9-]+", path.read_text(encoding="utf-8"))
    return out


def forbidden_in(result: Result, truth: Dict[str, Dict]) -> List[str]:
    """Chunks in the context that the user's REAL groups do not allow."""
    real_groups = list(result.user.groups) + [EVERYONE]
    bad = []
    for c in result.context:
        if not can_read(real_groups, truth[c["doc_id"]]["allowed_groups"]):
            bad.append(c["id"])
    return bad


def run_scenario(sc: Dict, policy: Dict[str, bool], store: VectorStore, use_llm: bool,
                 truth: Dict[str, Dict], tmpdir: Path) -> Tuple[Result, List[str]]:
    cache = AnswerCache(tmpdir / "cache_{}.json".format(sc["id"]))
    cache.clear()
    bot = Assistant(policy, store=store, cache=cache, use_llm=use_llm, audit=False, cache_without_llm=True)
    if sc.get("warm_cache_as"):
        bot.ask(TOKENS[sc["warm_cache_as"]], sc["question"])
    result = bot.ask(TOKENS[sc["user"]], sc["question"], claimed_groups=sc.get("claimed"))
    return result, forbidden_in(result, truth)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Lab 4 access-control attack suite")
    parser.add_argument("--llm", action="store_true", help="also generate answers (slow on CPU)")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the leaked chunk IDs")
    args = parser.parse_args(argv)

    policy = config.load_policy()
    store = VectorStore.load()
    truth = ground_truth_labels()
    marks = canaries()

    print("Policy  : " + "  ".join("{}={}".format(k.split("_")[0].upper(), "ON" if v else "off")
                                   for k, v in policy.items()))
    print("Index   : built with {} | embedder {}".format(
        "FIX3 ON" if store.meta.get("fix3_inherit_chunk_labels") else "FIX3 off", store.embedder.name))
    if store.meta.get("fix3_inherit_chunk_labels") != policy["fix3_inherit_chunk_labels"]:
        print("WARNING : policy.json and the index disagree on FIX3. Re-run:  python3 -m ragkit.ingest")
    print()
    print("{:<4} {:<58} {}".format("ID", "SCENARIO", "RESULT"))
    print("-" * 80)

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for sc in SCENARIOS:
            try:
                result, bad = run_scenario(sc, policy, store, args.llm, truth, Path(tmp))
            except LLMError as err:
                print("[error] {}".format(err))
                return 2
            if sc.get("expect") == "allowed":
                ok = any(c["doc_id"] == "restricted-vuln-exception-register" for c in result.context)
                status = "PASS  (authorised user still gets the data)" if ok else "FAIL  (over-blocking: legit user lost access)"
            else:
                ok = not bad
                via = " via cache" if result.cached else ""
                status = "BLOCKED" if ok else "LEAK{}  ({} forbidden chunk(s) in context)".format(via, len(bad))
                if args.llm and not ok:
                    leaked = [m for c in bad for m in marks.get(c.split("#")[0], []) if m in result.answer]
                    status += "  answer repeats: {}".format(", ".join(leaked) if leaked else "no canary")
            failures += 0 if ok else 1
            print("{:<4} {:<58} {}".format(sc["id"], sc["title"][:58], status))
            if args.verbose and sc.get("expect") != "allowed" and bad:
                print("     forbidden: {}".format(", ".join(bad)))

    print("-" * 80)
    print("All checks passed." if failures == 0 else "{} check(s) failing.".format(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
