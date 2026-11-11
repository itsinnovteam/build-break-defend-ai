"""
threat_model.py - derive a threat model from system_model.py.

Method (kept deliberately simple and repeatable):
  1. Find where untrusted input enters (the trust-boundary crossings).
  2. For each, name the realistic threats using STRIDE as a checklist
     (Spoofing, Tampering, Repudiation, Info disclosure, Denial of service, Elevation).
  3. Map every threat to the control that mitigates it (from controls.py),
     or mark it explicitly Accepted / Not-applicable with a reason.

No threat is left without a decision - that is what a CISO checks for.
"""
import controls
import system_model as sm

# Each threat: id, STRIDE category, the element it targets, description, and the
# control that handles it (or an explicit acceptance).
THREATS = [
    {"id": "T1", "stride": "Tampering/Elevation", "element": "TB1 model boundary (F3)",
     "desc": "The model is tricked into proposing a dangerous tool call (disable account, email out).",
     "control": "CTL-01", "status": "Mitigated"},
    {"id": "T2", "stride": "Elevation", "element": "TB2 untrusted content (F7)",
     "desc": "A ticket comment carries injected instructions that the agent might obey.",
     "control": "CTL-04", "status": "Mitigated"},
    {"id": "T3", "stride": "Information disclosure", "element": "TB2 -> outside",
     "desc": "Private logs/CMDB are exfiltrated to an external address via a tool.",
     "control": "CTL-08", "status": "Mitigated"},
    {"id": "T4", "stride": "Elevation", "element": "TB3 action boundary (F5)",
     "desc": "A write or external action runs without a human decision.",
     "control": "CTL-02", "status": "Mitigated"},
    {"id": "T5", "stride": "Tampering", "element": "TB3 action boundary (F5)",
     "desc": "An approved action is aimed at the wrong target (critical account, internal IP).",
     "control": "CTL-03", "status": "Mitigated"},
    {"id": "T6", "stride": "Denial of service", "element": "C2 agent loop",
     "desc": "A runaway or hijacked loop calls tools endlessly and exhausts the VM.",
     "control": "CTL-05", "status": "Mitigated"},
    {"id": "T7", "stride": "Repudiation", "element": "C6 state + audit",
     "desc": "An action happens with no record of who/what/when, so it cannot be reviewed.",
     "control": "CTL-06", "status": "Mitigated"},
    {"id": "T8", "stride": "Elevation", "element": "C5 MCP server",
     "desc": "A dangerous tool is reached through the MCP server directly.",
     "control": "CTL-07", "status": "Mitigated"},
    {"id": "T9", "stride": "Information disclosure", "element": "C4 model + data",
     "desc": "Data leaves the network by being sent to a third-party model API.",
     "control": "CTL-09", "status": "Mitigated"},
    {"id": "T10", "stride": "Tampering", "element": "C4 model supply chain",
     "desc": "The model is poisoned via training/fine-tuning data.",
     "control": None, "status": "Not applicable",
     "rationale": "We do not train or fine-tune; the open-weight model is fixed and version-pinned (LLM04)."},
    {"id": "T11", "stride": "Information disclosure", "element": "system prompt",
     "desc": "Secrets are extracted from the system prompt.",
     "control": None, "status": "Not applicable",
     "rationale": "The system prompt contains no secrets or credentials - only behavioural rules (LLM07)."},
]


def untrusted_entry_points():
    return sm.untrusted_entry_points()


def validate():
    """Every threat must reference a real control or carry an acceptance rationale."""
    problems = []
    control_ids = {c["id"] for c in controls.CONTROLS}
    for t in THREATS:
        if t["status"] == "Mitigated":
            if t["control"] not in control_ids:
                problems.append(f"{t['id']} mitigated but control {t['control']} not found")
        else:
            if not t.get("rationale"):
                problems.append(f"{t['id']} is {t['status']} but has no rationale")
    return problems


def summary():
    mit = sum(1 for t in THREATS if t["status"] == "Mitigated")
    na = sum(1 for t in THREATS if t["status"] == "Not applicable")
    return {"total": len(THREATS), "mitigated": mit, "not_applicable": na,
            "open": len(THREATS) - mit - na}


if __name__ == "__main__":
    print("Untrusted input enters at:")
    for p in untrusted_entry_points():
        print(f"  {p['flow']}: {p['from']} -> {p['to']}")
    print(f"\n{len(THREATS)} threats:")
    for t in THREATS:
        tag = t["control"] if t["control"] else t["status"]
        print(f"  {t['id']:4s} [{t['stride']:22s}] {t['status']:15s} -> {tag}")
    probs = validate()
    print("\nvalidation:", "OK - every threat has a decision" if not probs else probs)
    print("summary:", summary())
