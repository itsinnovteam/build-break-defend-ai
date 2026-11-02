"""Answer cache. CPU inference is slow, so caching answers is tempting.

The question is: what is the cache KEY? If two users with different
permissions can get the same key, the cache becomes a side door.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional

from . import config


def _normalise(question: str) -> str:
    return " ".join(question.lower().split())


class AnswerCache:
    def __init__(self, path: Path = config.CACHE_FILE):
        self.path = path
        self.entries: Dict[str, Dict] = {}
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                self.entries = json.load(fh)

    @staticmethod
    def make_key(question: str, scope: Optional[str]) -> str:
        # LAB4-BUG-4 when scope is None: the key is the question text only.
        # LAB4-FIX-4: scope = the caller's effective groups, so users with
        # different permissions never share an entry.
        material = _normalise(question) if scope is None else scope + "|" + _normalise(question)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def get(self, key: str) -> Optional[Dict]:
        return self.entries.get(key)

    def put(self, key: str, value: Dict) -> None:
        self.entries[key] = value
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.entries, fh, indent=1)

    def clear(self) -> None:
        self.entries = {}
        if self.path.exists():
            self.path.unlink()
