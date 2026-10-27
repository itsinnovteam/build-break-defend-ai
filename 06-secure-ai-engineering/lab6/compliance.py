"""
compliance.py - roll the control catalogue up into a compliance view.

For each framework, list which clauses our controls touch and which control(s)
provide the evidence. This is the "map our controls to the framework" table that
turns an engineering build into something an auditor or CISO can sign off.

Frameworks are examples, widely recognised. Replace clause ids with your own
framework's - the method (control -> clause -> evidence) is the transferable part.
"""
import controls

FRAMEWORKS = ["NIST AI RMF", "ISO 42001", "ISO 27001", "SOC 2"]

FRAMEWORK_NOTE = {
    "NIST AI RMF": "US AI Risk Management Framework - functions GOVERN / MAP / MEASURE / MANAGE.",
    "ISO 42001": "AI Management System standard - Annex A controls for responsible AI.",
    "ISO 27001": "Information security management - Annex A controls.",
    "SOC 2": "Trust Services Criteria (Security, Availability, Confidentiality, Privacy).",
}


def mapping(framework):
    """List (clause, [control ids], [evidence tests]) for one framework."""
    rows = {}
    for c in controls.CONTROLS:
        clause = c["compliance"].get(framework)
        if not clause:
            continue
        entry = rows.setdefault(clause, {"controls": [], "evidence": set()})
        entry["controls"].append(c["id"])
        entry["evidence"].update(c["evidence"])
    return {k: {"controls": v["controls"], "evidence": sorted(v["evidence"])} for k, v in sorted(rows.items())}


def coverage_counts():
    return {fw: len(mapping(fw)) for fw in FRAMEWORKS}


if __name__ == "__main__":
    for fw in FRAMEWORKS:
        m = mapping(fw)
        print(f"\n{fw}  ({len(m)} clauses touched)")
        for clause, info in m.items():
            print(f"  {clause:20s} <- {', '.join(info['controls'])}")
