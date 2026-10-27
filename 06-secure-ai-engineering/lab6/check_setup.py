"""check_setup.py - confirm the Lab 6 environment is ready. No model or GPU needed."""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f" ({detail})" if detail else ""))
    return ok


def main():
    print("Lab 6 setup check\n")
    ok = True
    ok &= check("Python 3.9+", sys.version_info >= (3, 9), sys.version.split()[0])
    try:
        import pytest  # noqa: F401
        ok &= check("pytest installed", True)
    except ImportError:
        ok &= check("pytest installed", False, "run: pip install -r requirements.txt")
    try:
        import bandit  # noqa: F401
        ok &= check("bandit installed", True)
    except ImportError:
        ok &= check("bandit installed", False, "run: pip install -r requirements.txt")

    # the governance modules all import and self-check
    mods = ["system_model", "controls", "owasp", "threat_model", "deployment", "compliance", "build_docs"]
    loaded = True
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception as exc:  # noqa: BLE001
            loaded = False
            print(f"FAIL  module {m} ({exc})")
    ok &= check(f"{len(mods)} governance modules import", loaded)

    import controls
    import threat_model
    import owasp
    ok &= check("controls have evidence tests", all(c["evidence"] for c in controls.CONTROLS),
                f"{len(controls.all_evidence_tests())} distinct tests")
    ok &= check("every threat has a decision", not threat_model.validate())
    ok &= check("every applicable OWASP risk is covered",
                set(owasp.gaps()) <= {"LLM04", "LLM07", "LLM08"},
                "LLM04/07/08 are N/A by design")

    # lab5 presence is optional (live evidence); not required to pass
    import link_lab5
    lab5 = link_lab5.find_lab5()
    check("lab5 found for live evidence (optional)", bool(lab5),
          str(lab5) if lab5 else "not found - recorded evidence will be used")

    print()
    if ok:
        print("All required checks passed. You are ready for Lab 6.")
        return 0
    print("Some checks failed. Fix the lines marked FAIL above, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
