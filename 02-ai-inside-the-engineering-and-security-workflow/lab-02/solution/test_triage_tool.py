"""
REFERENCE STRONG TESTS (instructor answer key).
One group per SPEC rule. Each test is written to FAIL if that rule is broken.
"""

import sqlite3

import pytest

from triage_tool import (
    block_ip,
    build_intel_request,
    check_reputation,
    is_brute_force,
    is_valid_ip,
    lookup_user,
    parse_failed_logins,
)

LINE_VALID = "Oct  8 09:00:14 bastion01 sshd[1]: Failed password for root from 198.51.100.23 port 1 ssh2"
LINE_INVALID_USER = "Oct  8 09:00:15 bastion01 sshd[2]: Failed password for invalid user oracle from 203.0.113.50 port 2 ssh2"
LINE_ACCEPTED = "Oct  8 09:00:16 bastion01 sshd[3]: Accepted publickey for jdelacruz from 10.10.5.21 port 3 ssh2"


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (username TEXT, department TEXT)")
    conn.execute("INSERT INTO users VALUES ('mreyes', 'Finance')")
    conn.execute("INSERT INTO users VALUES ('jdelacruz', 'IT Ops')")
    conn.commit()
    return conn


# ---- R1 parse_failed_logins -------------------------------------------------
def test_r1_counts_normal_failed_login():
    assert parse_failed_logins([LINE_VALID, LINE_VALID]) == {"198.51.100.23": 2}


def test_r1_counts_invalid_user_attempts():
    assert parse_failed_logins([LINE_INVALID_USER]) == {"203.0.113.50": 1}


def test_r1_ignores_successful_logins():
    assert parse_failed_logins([LINE_ACCEPTED]) == {}


# ---- R2 is_brute_force (boundary values) ------------------------------------
@pytest.mark.parametrize("count, expected", [(4, False), (5, True), (6, True)])
def test_r2_threshold_boundary(count, expected):
    assert is_brute_force(count) is expected


# ---- R3 is_valid_ip ----------------------------------------------------------
@pytest.mark.parametrize("ip", ["10.10.5.21", "0.0.0.0", "255.255.255.255"])
def test_r3_accepts_real_ipv4(ip):
    assert is_valid_ip(ip) is True


@pytest.mark.parametrize(
    "ip", ["999.1.1.1", "256.0.0.1", "1.2.3", "abc", "", "1.2.3.4; rm -rf /",
           "::1", "2001:db8::1"]
)
def test_r3_rejects_bad_input(ip):
    assert is_valid_ip(ip) is False


# ---- R4 lookup_user ----------------------------------------------------------
def test_r4_finds_existing_user():
    assert lookup_user(make_db(), "mreyes") == ("mreyes", "Finance")


def test_r4_unknown_user_returns_none():
    assert lookup_user(make_db(), "nobody") is None


def test_r4_sql_injection_returns_none():
    assert lookup_user(make_db(), "x' OR '1'='1") is None


# ---- R5 check_reputation (fail closed) --------------------------------------
def test_r5_known_ip_returns_feed_verdict():
    assert check_reputation("203.0.113.50", {"203.0.113.50": "malicious"}) == "malicious"


def test_r5_ip_not_in_feed_is_unknown():
    assert check_reputation("198.51.100.23", {"203.0.113.50": "malicious"}) == "unknown"


def test_r5_missing_feed_is_unknown():
    assert check_reputation("198.51.100.23", None) == "unknown"


# ---- R6 build_intel_request (no hardcoded secret) ---------------------------
def test_r6_uses_token_from_environment(monkeypatch):
    monkeypatch.setenv("THREAT_INTEL_TOKEN", "test-token-123")
    req = build_intel_request("203.0.113.50")
    assert req["headers"]["Authorization"] == "Bearer test-token-123"


def test_r6_missing_token_raises(monkeypatch):
    monkeypatch.delenv("THREAT_INTEL_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        build_intel_request("203.0.113.50")


# ---- R7 block_ip -------------------------------------------------------------
def test_r7_valid_ip_is_written(tmp_path):
    path = tmp_path / "blocklist.txt"
    block_ip("203.0.113.50", str(path))
    assert path.read_text(encoding="utf-8").strip() == "BLOCK 203.0.113.50"


def test_r7_injection_attempt_is_rejected(tmp_path):
    path = tmp_path / "blocklist.txt"
    with pytest.raises(ValueError):
        block_ip("1.2.3.4 && echo INJECTED", str(path))
    assert not path.exists()
