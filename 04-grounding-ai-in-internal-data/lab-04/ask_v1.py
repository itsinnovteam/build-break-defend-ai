"""ask_v1.py - the VULNERABLE assistant (v1), for Phase 4 only. Never build it this way.

Example:  python ask_v1.py --user dana "What are the salary bands for senior engineers?"
"""
import sys

from assistant import run_cli

if __name__ == "__main__":
    sys.exit(run_cli("v1"))
