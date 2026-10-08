"""
meta_test.py  -  "Test the tests."

How it works (a fire drill for your test suite):
  1. Your test file is run against CORRECT code     -> it must PASS.
  2. Your test file is run against 7 BROKEN copies   -> it should FAIL on each.
     A broken copy that still passes = a bug your tests would let into production.

Usage (from the lab2 folder):
    python meta_test.py                      # checks test_triage_tool.py
    python meta_test.py my_other_tests.py    # checks another test file

Runs on CPU only, needs no network, and never modifies your files.
"""

import os
import shutil
import subprocess
import sys
import tempfile
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
META = HERE / "meta"
TIMEOUT_SECONDS = 60

BUGS = [
    ("bug1_misses_invalid_user", "R1  'invalid user' attacks not counted"),
    ("bug2_off_by_one", "R2  exactly 5 failures not flagged"),
    ("bug3_weak_ip_check", "R3  999.1.1.1 accepted as an IP"),
    ("bug4_sql_injection", "R4  SQL injection in lookup_user"),
    ("bug5_fail_open", "R5  unknown IP reported as 'clean'"),
    ("bug6_hardcoded_token_fallback", "R6  hardcoded token fallback"),
    ("bug7_no_ip_validation", "R7  block_ip accepts any input"),
]


def run_tests(test_file, code_file):
    """Copy test_file + code_file (as triage_tool.py) into a private temp folder
    and run pytest there.

    Returns (code, output). code is pytest's exit code (0 = all passed,
    1 = some failed, 2/3/4 = could not run, 5 = no tests found) or "timeout".
    """
    with _TempDir() as tmp:
        tmp = Path(tmp)
        shutil.copy(code_file, tmp / "triage_tool.py")
        shutil.copy(test_file, tmp / test_file.name)
        if (HERE / "sample_auth.log").exists():
            shutil.copy(HERE / "sample_auth.log", tmp / "sample_auth.log")
        # Our own empty config, so a pytest config in a parent folder
        # (e.g. the user's home folder) cannot change how the tests run.
        (tmp / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for name in ("THREAT_INTEL_TOKEN", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
            env.pop(name, None)  # tests must not depend on these
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 "--tb=short", test_file.name],
                cwd=tmp, env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return "timeout", ""
        return result.returncode, (result.stdout or "") + (result.stderr or "")


STEP1_HELP = {
    1: ("Your tests FAIL on correct code, so at least one test expects the wrong\n"
        "behaviour. Compare the failing test with SPEC.md and fix the TEST."),
    2: ("pytest could not load your test file: a syntax error, or an import of a\n"
        "function name that does not exist in SPEC.md. Read the error below."),
    3: "pytest hit an internal error. Read the error below.",
    4: "pytest could not start (bad command or option). Read the error below.",
    5: ("No tests were found. Every test function must start with 'test_' and the\n"
        "file name must be the test file you meant to check."),
    "timeout": (f"Your tests did not finish within {TIMEOUT_SECONDS} seconds. A test probably\n"
                "waits forever (a loop, input(), or a network call). Fix that test."),
}


def main():
    if not META.is_dir() or not (META / "reference.py").exists():
        sys.exit("The meta folder is missing. Run this script from an unchanged lab2 folder.")
    test_file = Path(sys.argv[1] if len(sys.argv) > 1 else "test_triage_tool.py").resolve()
    if not test_file.exists():
        sys.exit(f"Test file not found: {test_file}\nRun this command from inside the lab2 folder.")

    print(f"\nMETA-TEST of: {test_file.name}\n" + "=" * 60)

    code, output = run_tests(test_file, META / "reference.py")
    if code != 0:
        print("STEP 1  Your tests on CORRECT code ........ FAIL\n")
        print(STEP1_HELP.get(code, f"pytest stopped with exit code {code}. Read the output below."))
        if output:
            print("\npytest said:\n")
            print(output[-2500:])
        sys.exit(1)
    print("STEP 1  Your tests on CORRECT code ........ PASS (good)\n")

    print("STEP 2  Your tests on 7 BROKEN versions:")
    caught = 0
    for name, description in BUGS:
        code, _ = run_tests(test_file, META / f"{name}.py")
        if code == 1:
            status = "CAUGHT"
            caught += 1
        elif code == 0:
            status = "MISSED  <-- this bug would reach production"
        elif code == "timeout":
            status = "TIMEOUT (a test hangs on this bug - make it fail fast)"
        else:
            status = f"ERROR (pytest exit code {code})"
        print(f"  {description:<42} {status}")

    print("=" * 60)
    print(f"SCORE: your tests caught {caught} of {len(BUGS)} planted bugs.")
    if caught == len(BUGS):
        print("Excellent. Remember: this measures your tests, not your code.")
    else:
        print("Add a test for each MISSED rule (see SPEC.md), then run again.")


if __name__ == "__main__":
    main()
