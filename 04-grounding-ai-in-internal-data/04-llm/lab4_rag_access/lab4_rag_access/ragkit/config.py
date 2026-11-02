"""Lab 4 settings: paths, model names and the access-control policy toggles.

Everything can be overridden with environment variables so the same code runs
on every learner VM without editing Python files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
USERS_FILE = DATA_DIR / "users.json"
INDEX_FILE = DATA_DIR / "index.json"
CACHE_FILE = DATA_DIR / "answer_cache.json"
AUDIT_LOG = DATA_DIR / "audit.jsonl"
POLICY_FILE = ROOT / "policy.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
CHAT_MODEL = os.environ.get("LAB4_CHAT_MODEL", "llama3.1:8b")
EMBED_MODEL = os.environ.get("LAB4_EMBED_MODEL", "nomic-embed-text")
# CPU-only VM: keep the context small so answers come back in reasonable time.
NUM_CTX = int(os.environ.get("LAB4_NUM_CTX", "4096"))
NUM_PREDICT = int(os.environ.get("LAB4_NUM_PREDICT", "350"))
LLM_TIMEOUT = int(os.environ.get("LAB4_LLM_TIMEOUT", "600"))
TOP_K = int(os.environ.get("LAB4_TOP_K", "3"))

# Every policy starts in its VULNERABLE state. Part C of the lab flips them.
POLICY_DEFAULTS: Dict[str, bool] = {
    "fix1_filter_at_retrieval": False,   # False = access rules live only in the prompt
    "fix2_ignore_caller_groups": False,  # False = trust groups the caller claims
    "fix3_inherit_chunk_labels": False,  # False = only the first chunk keeps its label
    "fix4_cache_per_user": False,        # False = one answer cache shared by everyone
}

POLICY_DESCRIPTIONS: Dict[str, str] = {
    "fix1_filter_at_retrieval": "Enforce permissions in the retriever, not the prompt",
    "fix2_ignore_caller_groups": "Take groups from the identity provider only",
    "fix3_inherit_chunk_labels": "Every chunk inherits its document's label (re-ingest!)",
    "fix4_cache_per_user": "Scope the answer cache to the caller's permissions",
}


def load_policy() -> Dict[str, bool]:
    policy = dict(POLICY_DEFAULTS)
    if POLICY_FILE.exists():
        with POLICY_FILE.open(encoding="utf-8") as fh:
            stored = json.load(fh)
        for key in POLICY_DEFAULTS:
            if key in stored:
                policy[key] = bool(stored[key])
    return policy


def save_policy(policy: Dict[str, bool]) -> None:
    with POLICY_FILE.open("w", encoding="utf-8") as fh:
        json.dump(policy, fh, indent=2)
        fh.write("\n")
