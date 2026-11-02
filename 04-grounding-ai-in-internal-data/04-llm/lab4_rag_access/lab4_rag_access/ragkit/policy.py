"""Show or change the access-control fixes.

    python3 -m ragkit.policy                 # show current state
    python3 -m ragkit.policy --enable 1      # switch on LAB4-FIX-1
    python3 -m ragkit.policy --disable 3
    python3 -m ragkit.policy --all-off       # back to fully vulnerable
"""
from __future__ import annotations

import argparse

from . import config


def key_for(n: int) -> str:
    for key in config.POLICY_DEFAULTS:
        if key.startswith("fix{}_".format(n)):
            return key
    raise SystemExit("There is no fix {}. Valid: 1-4".format(n))


def show(policy) -> None:
    for key, value in policy.items():
        print("  [{}] {}  {}".format("ON " if value else "off", key, "- " + config.POLICY_DESCRIPTIONS[key]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Toggle Lab 4 fixes")
    parser.add_argument("--enable", type=int, action="append", default=[])
    parser.add_argument("--disable", type=int, action="append", default=[])
    parser.add_argument("--all-off", action="store_true")
    parser.add_argument("--all-on", action="store_true")
    args = parser.parse_args()

    policy = config.load_policy()
    before_fix3 = policy["fix3_inherit_chunk_labels"]
    if args.all_off or args.all_on:
        policy = {k: bool(args.all_on) for k in policy}
    for n in args.enable:
        policy[key_for(n)] = True
    for n in args.disable:
        policy[key_for(n)] = False
    config.save_policy(policy)
    show(policy)
    if policy["fix3_inherit_chunk_labels"] != before_fix3:
        print("\nFIX-3 changes how chunks are labelled at ingest time. Re-run:  python3 -m ragkit.ingest")


if __name__ == "__main__":
    main()
