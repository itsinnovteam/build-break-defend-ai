"""
demo_attacks.py  -  SAFE proof that the AI code is broken, even though its tests pass.

Every demo is harmless: it only uses the lab's sample data, an in-memory
database, and a temporary folder that is deleted afterwards.

Usage (from the lab2 folder):
    python demo_attacks.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import triage_tool as t

print("\nDEMO 1 - The biggest attacker is invisible (R1)")
with open(Path(__file__).resolve().parent / "sample_auth.log", encoding="utf-8") as f:
    lines = f.readlines()
attacker_lines = [ln for ln in lines if "203.0.113.50" in ln]
counts = t.parse_failed_logins(lines)
print(f"  Lines in the log from 203.0.113.50 : {len(attacker_lines)}")
print(f"  Failures the tool counted for it    : {counts.get('203.0.113.50', 0)}")

print("\nDEMO 2 - Exactly 5 failures (R2)")
print(f"  is_brute_force(5) returned          : {t.is_brute_force(5)}   (SPEC says True)")

print("\nDEMO 3 - Impossible IP accepted (R3)")
print(f"  is_valid_ip('999.1.1.1') returned   : {t.is_valid_ip('999.1.1.1')}   (SPEC says False)")

print("\nDEMO 4 - SQL injection (R4)")
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE users (username TEXT, department TEXT)")
conn.execute("INSERT INTO users VALUES ('mreyes', 'Finance')")
evil = "x' OR '1'='1"
result = t.lookup_user(conn, evil)
print(f"  lookup_user(conn, {evil!r})  : {result}   (SPEC says None)")

print("\nDEMO 5 - Fail open (R5)")
print(f"  check_reputation('198.51.100.23', {{}}) : {t.check_reputation('198.51.100.23', {})!r}   (SPEC says 'unknown')")

print("\nDEMO 6 - Command injection (R7)  [harmless: only runs 'echo']")
# Work inside a private temporary folder, using a short relative file name,
# so nothing can ever be written outside that folder (even if the folder's
# path contains spaces, e.g. C:\Users\Juan Dela Cruz\AppData\Local\Temp).
original_dir = os.getcwd()
tmp = tempfile.mkdtemp()
os.chdir(tmp)
try:
    sys.stdout.flush()
    t.block_ip("1.2.3.4 && echo INJECTED-COMMAND-RAN", "blocklist.txt")
    sys.stdout.flush()
    print("  block_ip accepted the input. If you see INJECTED-COMMAND-RAN")
    print("  above or below, an attacker-controlled command was executed.")
    if os.path.exists("blocklist.txt"):
        with open("blocklist.txt", encoding="utf-8", errors="replace") as f:
            print("  blocklist.txt now contains:", f.read().strip().replace("\n", " | "))
except ValueError as exc:
    print(f"  Rejected (good): {exc}")
finally:
    os.chdir(original_dir)
    shutil.rmtree(tmp, ignore_errors=True)

print("\nCompare every result with SPEC.md. On the original AI code, all 6 demos")
print("break the SPEC while all 6 AI-written tests pass. That is the lesson.\n")
