"""
check_fix.py  -  Independent check of YOUR fixed triage_tool.py against SPEC.md.

It runs the instructor's reference tests (checker/reference_tests.py) against
the triage_tool.py in this folder and reports PASS/FAIL per SPEC rule.

Usage (from the lab2 folder):
    python check_fix.py

Runs on CPU only, needs no network, and never modifies your files.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

if sys.version_info < (3, 9):
    sys.exit("Python 3.9 or newer is required. You have " + sys.version.split()[0] + ".")

HERE = Path(__file__).resolve().parent

class _TempDir:
    """A private temporary folder that is always removed afterwards.
    (Works on Python 3.9, the default on the Module 0 VM.)"""

    def __enter__(self):
        self.path = tempfile.mkdtemp()
        return self.path

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)
        return False
TIMEOUT_SECONDS = 60

RULES = {
    "r1": "R1  count 'invalid user' attacks",
    "r2": "R2  5 or more failures = brute force",
    "r3": "R3  strict IPv4 validation",
    "r4": "R4  parameterized SQL (no injection)",
    "r5": "R5  fail closed ('unknown', not 'clean')",
    "r6": "R6  token from environment, not code",
    "r7": "R7  block_ip validates, no shell",
}


def main():
    code_file = HERE / "triage_tool.py"
    ref_tests = HERE / "checker" / "reference_tests.py"
    if not code_file.exists():
        sys.exit("triage_tool.py not found. Run this command from inside the lab2 folder.")
    if not ref_tests.exists():
        sys.exit("checker/reference_tests.py is missing. Use an unchanged lab2 folder.")

    with _TempDir() as tmp:
        tmp = Path(tmp)
        shutil.copy(code_file, tmp / "triage_tool.py")
        shutil.copy(ref_tests, tmp / "test_reference.py")
        if (HERE / "sample_auth.log").exists():
            shutil.copy(HERE / "sample_auth.log", tmp / "sample_auth.log")
        # Our own empty config, so a pytest config in a parent folder cannot interfere.
        (tmp / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        report = tmp / "report.xml"

        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for name in ("THREAT_INTEL_TOKEN", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
            env.pop(name, None)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=short",
                 f"--junitxml={report}", "test_reference.py"],
                cwd=tmp, env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            sys.exit(f"The checks did not finish within {TIMEOUT_SECONDS} seconds. Something in "
                     "triage_tool.py waits forever (a loop, input(), or a network call).")
        output = (result.stdout or "") + (result.stderr or "")

        failed = {key: 0 for key in RULES}
        total = {key: 0 for key in RULES}
        if report.exists():
            for case in ET.parse(report).getroot().iter("testcase"):
                key = case.get("name", "")[5:7]  # "test_r1_..." -> "r1"
                if key in total:
                    total[key] += 1
                    if case.find("failure") is not None or case.find("error") is not None:
                        failed[key] += 1

    if sum(total.values()) == 0:
        print(output[-2500:])
        sys.exit("No checks ran: triage_tool.py has a syntax error, or a function was renamed "
                 "or removed (see the error above).\nTip: run  python -c \"import triage_tool\"  "
                 "to see the error.")

    print("\nCHECK OF YOUR FIX (triage_tool.py vs SPEC.md)\n" + "=" * 60)
    passed_rules = 0
    for key, label in RULES.items():
        ok = total[key] > 0 and failed[key] == 0
        passed_rules += ok
        status = "PASS" if ok else f"FAIL ({failed[key]} of {total[key]} checks)"
        print(f"  {label:<44} {status}")
    print("=" * 60)
    print(f"RESULT: {passed_rules} of {len(RULES)} rules satisfied.")
    if passed_rules < len(RULES):
        print("Give the AI the failing rule from SPEC.md and ask it to fix ONLY that.")


if __name__ == "__main__":
    main()
