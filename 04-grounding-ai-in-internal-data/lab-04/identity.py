"""
identity.py - WHO is asking (authentication) and WHAT they may see (authorization).

In the lab, --user stands in for the login that your company SSO has already checked
(authentication). The ROLES are looked up here, on the server side, in
config/directory.json (authorization). Nothing the user types - not the question, not a
command-line option - can add a role.

Every problem fails CLOSED: unknown user, no roles, a missing or broken directory file
-> AccessDenied, and nothing is retrieved.
"""

import json
import re

import config

USER_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}")


class AccessDenied(Exception):
    """No valid authorization context: deny, retrieve nothing."""


def load_directory(path=None):
    path = path or config.DIRECTORY_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        users = data["users"]
        if not isinstance(users, dict):
            raise TypeError("users must be an object")
    except FileNotFoundError:
        raise AccessDenied("directory file not found - access denied (fail closed)") from None
    except (OSError, ValueError, KeyError, TypeError):
        raise AccessDenied("directory file is unreadable or invalid - access denied (fail closed)") from None
    return users


def resolve_roles(user_id, directory=None):
    """Return the trusted roles of user_id, or raise AccessDenied."""
    if not isinstance(user_id, str) or not USER_ID.fullmatch(user_id):
        raise AccessDenied("missing or invalid user id - access denied")
    users = load_directory() if directory is None else directory
    entry = users.get(user_id)
    if not isinstance(entry, dict):
        raise AccessDenied(f"unknown user '{user_id}' - access denied")
    roles = entry.get("roles")
    if not isinstance(roles, list):
        raise AccessDenied(f"user '{user_id}' has no valid roles - access denied")
    known = [r for r in roles if r in config.KNOWN_ROLES]     # unknown role names are ignored
    if not known:
        raise AccessDenied(f"user '{user_id}' has no valid roles - access denied")
    return sorted(set(known))
