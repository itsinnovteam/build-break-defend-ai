"""
link_lab5.py - attach LIVE evidence by running the Lab 5 test suite, if it is next to us.

The control document cites Lab 5 tests as evidence. This script finds the lab5 folder
(a sibling of lab6, or $LAB5_DIR), runs pytest there, and reports which of the cited
evidence tests passed. If lab5 is not present, it says so and the rest of Lab 6 still
works - the document then cites the tests by name as recorded evidence.

Nothing in Lab 6 depends on this running. It is the "prove it live" button.
"""
import os
import subprocess  # nosec B404 - we run pytest on our own trusted lab, no shell, fixed args
import sys
from pathlib import Path

import controls

HERE = Path(__file__).resolve().parent


def find_lab5():
    for cand in [os.environ.get("LAB5_DIR"), HERE.parent / "lab5", HERE.parent.parent / "Module5" / "lab5"]:
        if cand and Path(cand).joinpath("tests", "test_lab5.py").exists():
            return Path(cand)
    return None


def run():
    lab5 = find_lab5()
    cited = controls.all_evidence_tests()
    if not lab5:
        print("lab5 folder not found (looked for ../lab5 and $LAB5_DIR).")
        print(f"The control document cites {len(cited)} Lab 5 tests as recorded evidence:")
        for t in cited:
            print(f"  - {t}")
        print("\nPlace the lab5 folder beside lab6 (or set LAB5_DIR) to run them live.")
        return 0
    print(f"Running Lab 5 evidence tests in: {lab5}")
    py = sys.executable
    proc = subprocess.run(  # nosec B603 - fixed args, no shell, trusted lab code
        [py, "-m", "pytest", "-q", "tests/test_lab5.py"],
        cwd=str(lab5), capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    print(tail)
    ok = proc.returncode == 0
    print("LIVE EVIDENCE:", "all cited controls are backed by passing tests" if ok
          else "some tests failed - see output above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
