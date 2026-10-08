"""
META-TEST VARIANT: bug4_sql_injection
Bug: SQL built with an f-string (R4).
Do not edit. Used only by meta_test.py.

Each fix is tagged with the SPEC rule it satisfies (R1..R7).
"""

import ipaddress
import os
import re

INTEL_URL = "https://intel.example.internal/v1/ip/"

# R1: optional "invalid user " so attacks on non-existent accounts are counted
FAILED_LOGIN = re.compile(r"Failed password for (?:invalid user )?(\S+) from (\S+)")


def parse_failed_logins(lines):
    """Return a dict {ip: number_of_failed_logins} from SSH auth log lines."""
    counts = {}
    for line in lines:
        match = FAILED_LOGIN.search(line)
        if match:
            ip = match.group(2)
            counts[ip] = counts.get(ip, 0) + 1
    return counts


def is_brute_force(count, threshold=5):
    """R2: True when there are 5 or more failures."""
    return count >= threshold


def is_valid_ip(ip):
    """R3: True only for a real IPv4 address. Never raises."""
    if not isinstance(ip, str):
        return False
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def lookup_user(conn, username):
    """R4: parameterized query - the database treats username as data, not SQL."""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT username, department FROM users WHERE username = '{username}'"
    )
    return cursor.fetchone()


def check_reputation(ip, feed):
    """R5: fail closed - no data means 'unknown', never 'clean'."""
    if not feed:
        return "unknown"
    return feed.get(ip, "unknown")


def build_intel_request(ip):
    """R6: token comes from the environment, never from source code."""
    token = os.environ.get("THREAT_INTEL_TOKEN")
    if not token:
        raise RuntimeError("THREAT_INTEL_TOKEN environment variable is not set")
    return {
        "url": INTEL_URL + ip,
        "headers": {"Authorization": "Bearer " + token},
    }


def block_ip(ip, blocklist_path="blocklist.txt"):
    """R7: validate first, then write the file directly - no shell at all."""
    if not is_valid_ip(ip):
        raise ValueError(f"Refusing to block invalid IP: {ip!r}")
    with open(blocklist_path, "a", encoding="utf-8") as f:
        f.write(f"BLOCK {ip}\n")


if __name__ == "__main__":
    with open("sample_auth.log", encoding="utf-8") as f:
        results = parse_failed_logins(f)
    for ip, count in sorted(results.items(), key=lambda x: -x[1]):
        flag = "BRUTE FORCE" if is_brute_force(count) else "ok"
        print(f"{ip:<16} {count:>3} failures   {flag}")
