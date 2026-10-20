"""ask.py - the SECURE assistant (v2): access control at retrieval.

Example:  python ask.py --user ana "Who approves a Tenable risk exception?"
"""
import sys

from assistant import run_cli

if __name__ == "__main__":
    sys.exit(run_cli("v2"))
