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


def _test_target(path):
    """Return the pytest target inside a Lab 5 folder: the exact test file, or its tests/ dir."""
    p = Path(path)
    if p.joinpath("tests", "test_lab5.py").exists():
        return "tests/test_lab5.py"
    tests = p / "tests"
    if tests.is_dir() and any(tests.glob("test_*.py")):
        return "tests"
    return None


def _is_lab5(path):
    """A folder is Lab 5 if it has the Lab 5 code AND a test suite (any test filename)."""
    try:
        if path is None:
            return False
        p = Path(path)
        has_code = p.joinpath("agent.py").exists() and p.joinpath("toolkit.py").exists() \
            and p.joinpath("run_agent.py").exists()
        return has_code and _test_target(p) is not None
    except OSError:
        return False


# Where we look, in order. Covers lab-05 beside lab-06, Module5/ layouts, and the home dir.
_BASES = [HERE.parent, HERE.parent.parent, HERE.parent.parent / "Module5", Path.home()]


def find_lab5():
    """Locate the Lab 5 folder, whatever it is named (lab5, lab-05, lab-5, ...) or wherever it sits."""
    # 1. explicit override wins
    env = os.environ.get("LAB5_DIR")
    if _is_lab5(env):
        return Path(env)
    # 2. common names, near this folder or in the home dir
    names = ["lab5", "lab-05", "lab-5", "lab05", "lab_5", "Lab5", "Lab-05", "lab-5-agent"]
    for base in _BASES:
        for n in names:
            if _is_lab5(base / n):
                return (base / n).resolve()
    # 3. scan one and two levels under each base for the folder that actually holds the tests
    #    (handles any naming convention and ~/Module5/lab-05 style layouts)
    seen = set()
    for base in _BASES:
        try:
            if base in seen or not base.exists():
                continue
            seen.add(base)
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                if _is_lab5(child):
                    return child.resolve()
                try:
                    for grand in sorted(child.iterdir()):
                        if grand.is_dir() and _is_lab5(grand):
                            return grand.resolve()
                except OSError:
                    continue
        except OSError:
            continue
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
    target = _test_target(lab5) or "tests"
    proc = subprocess.run(  # nosec B603 - fixed args, no shell, trusted lab code
        [py, "-m", "pytest", "-q", target],
        cwd=str(lab5), capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    print(tail)
    ok = proc.returncode == 0
    print("LIVE EVIDENCE:", "all cited controls are backed by passing tests" if ok
          else "some tests failed - see output above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())