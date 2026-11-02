"""Who is asking, and which groups are they really in?

users.json simulates the identity provider (Entra ID, Okta, OCI IAM...). The
token stands in for a signed SSO session. In the CLI, --groups simulates an
HTTP header such as `X-User-Groups` that the CLIENT sends - and the client is
controlled by the user.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config

EVERYONE = "everyone"


@dataclass
class User:
    token: str
    username: str
    name: str
    role: str
    groups: List[str]


def load_users() -> Dict[str, User]:
    with config.USERS_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {u["token"]: User(**u) for u in data["users"]}


def authenticate(token: Optional[str]) -> User:
    if not token:
        raise SystemExit("No session token. Pass --token or run:  export LAB4_TOKEN=<token>")
    users = load_users()
    if token not in users:
        raise SystemExit("Unknown or expired token: {}".format(token))
    return users[token]


def effective_groups(user: User, claimed_groups: Optional[List[str]], policy: Dict[str, bool]) -> List[str]:
    """Return the groups used for authorisation decisions."""
    if claimed_groups and not policy["fix2_ignore_caller_groups"]:
        # LAB4-BUG-2: the caller says which groups they are in, and we believe
        # them. Equivalent to trusting an X-User-Groups header or a 'role' field
        # in a JSON request body.
        return sorted(set(claimed_groups) | {EVERYONE})
    # LAB4-FIX-2: groups come only from the identity provider. Any claimed
    # groups are ignored (and recorded in the audit log by the caller).
    return sorted(set(user.groups) | {EVERYONE})


def can_read(groups: List[str], allowed_groups: List[str]) -> bool:
    return bool(set(groups) & set(allowed_groups))
