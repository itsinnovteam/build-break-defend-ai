"""Start the lab again:  python3 -m ragkit.reset

Turns every fix off, deletes the cache, audit log and index.
"""
from __future__ import annotations

from . import config


def main() -> None:
    config.save_policy(dict(config.POLICY_DEFAULTS))
    for path in (config.CACHE_FILE, config.AUDIT_LOG, config.INDEX_FILE):
        if path.exists():
            path.unlink()
            print("removed", path.relative_to(config.ROOT))
    print("All fixes OFF. Next:  python3 -m ragkit.ingest")


if __name__ == "__main__":
    main()
