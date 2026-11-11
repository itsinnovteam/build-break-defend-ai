"""
system_model.py - a machine-readable description of the system we are securing:
the SOC triage agent built in Lab 5.

Everything else in Lab 6 (the threat model, the control matrix, the compliance
mapping, the CISO document) is DERIVED from this one file. Change the system here
and every artifact updates - so the paperwork can never drift from the real build.

Pure data + Python standard library. No model, no network, no GPU.
"""

SYSTEM = {
    "name": "SOC Triage Agent",
    "version": "1.0 (Lab 5, defended / v2)",
    "owner": "Security Operations / Innovation Team",
    "purpose": "Investigate a SOC alert using read-only tools and recommend an action for a human to approve.",
    "hosting": "Self-hosted on an internal VM (Oracle Linux 9). Local open-weight model via Ollama. No data leaves the network.",
}

# ---- Components: the moving parts of the system ------------------------------
# zone: where it runs. "internal" = our VM; "model" = the local LLM; "external" = outside our control.
COMPONENTS = [
    {"id": "C1", "name": "Operator / analyst", "zone": "internal", "desc": "The human who starts a triage and approves risky actions."},
    {"id": "C2", "name": "Agent loop (agent.py)", "zone": "internal", "desc": "Orchestrates think-act-observe; calls the trust boundary for every tool."},
    {"id": "C3", "name": "Trust boundary (handle_call)", "zone": "internal", "desc": "The one function that allows, denies or validates every tool call."},
    {"id": "C4", "name": "Local LLM (llama3.1:8b via Ollama)", "zone": "model", "desc": "Proposes tool calls and writes the final answer. Untrusted decision-maker."},
    {"id": "C5", "name": "Tools (toolkit.py) + MCP server", "zone": "internal", "desc": "The 8 SOC tools; the MCP server exposes only the read-only ones."},
    {"id": "C6", "name": "Local state (state/, audit log)", "zone": "internal", "desc": "Case notes, blocklist, outbox and the audit log - local files only."},
    {"id": "C7", "name": "Alert + ticket data (scenarios/)", "zone": "internal", "desc": "SOC alerts. Ticket COMMENTS may be written by outsiders - untrusted content."},
]

# ---- Data flows: who sends what to whom -------------------------------------
# untrusted=True marks a flow that can carry attacker-controlled content.
DATA_FLOWS = [
    {"id": "F1", "frm": "C1", "to": "C2", "data": "Triage task (which alert)", "untrusted": False},
    {"id": "F2", "frm": "C2", "to": "C4", "data": "Task + tool menu + observations so far", "untrusted": False},
    {"id": "F3", "frm": "C4", "to": "C2", "data": "A proposed tool call (name + arguments)", "untrusted": True},
    {"id": "F4", "frm": "C2", "to": "C3", "data": "The proposed tool call, for a decision", "untrusted": True},
    {"id": "F5", "frm": "C3", "to": "C5", "data": "An allowed tool call", "untrusted": False},
    {"id": "F6", "frm": "C5", "to": "C7", "data": "Reads alert + ticket comments", "untrusted": False},
    {"id": "F7", "frm": "C7", "to": "C2", "data": "Tool result incl. outsider-written comment", "untrusted": True},
    {"id": "F8", "frm": "C5", "to": "C6", "data": "Writes case note / blocklist / audit entry", "untrusted": False},
    {"id": "F9", "frm": "C3", "to": "C1", "data": "Approval request for a write/external action", "untrusted": False},
]

# ---- Trust boundaries: lines where trust changes ----------------------------
# Untrusted input ENTERS the system wherever an untrusted flow crosses into "internal".
TRUST_BOUNDARIES = [
    {"id": "TB1", "name": "Model boundary",
     "between": ["model", "internal"],
     "crossing_flows": ["F3", "F4"],
     "note": "The LLM is untrusted: anything it proposes (F3) is a REQUEST, never an order. handle_call (C3) is the gate."},
    {"id": "TB2", "name": "Untrusted-content boundary",
     "between": ["external", "internal"],
     "crossing_flows": ["F7"],
     "note": "Ticket comments can be written by outsiders. They arrive as tool results (F7) and must be treated as DATA, never instructions."},
    {"id": "TB3", "name": "Action boundary",
     "between": ["internal", "internal"],
     "crossing_flows": ["F5", "F8", "F9"],
     "note": "Any action that changes state or reaches outside needs least privilege, argument checks and (for write/extern) human approval."},
]

# Where does untrusted input enter? (the question the CISO asks first)
def untrusted_entry_points():
    pts = []
    for f in DATA_FLOWS:
        if f["untrusted"]:
            frm = component(f["frm"])
            to = component(f["to"])
            pts.append({"flow": f["id"], "from": frm["name"], "to": to["name"], "data": f["data"]})
    return pts


def component(cid):
    for c in COMPONENTS:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


# ---- Data classes handled (for data governance) -----------------------------
DATA_ASSETS = [
    {"id": "D1", "name": "Alert metadata", "sensitivity": "internal", "pii": False, "residency": "on-VM"},
    {"id": "D2", "name": "Authentication logs", "sensitivity": "confidential", "pii": True, "residency": "on-VM"},
    {"id": "D3", "name": "Asset owner / CMDB", "sensitivity": "confidential", "pii": True, "residency": "on-VM"},
    {"id": "D4", "name": "Ticket comments (may be outsider-written)", "sensitivity": "untrusted-input", "pii": False, "residency": "on-VM"},
    {"id": "D5", "name": "Case notes + audit log", "sensitivity": "confidential", "pii": False, "residency": "on-VM"},
]

if __name__ == "__main__":
    print(f"System: {SYSTEM['name']} ({SYSTEM['version']})")
    print(f"  components: {len(COMPONENTS)}  flows: {len(DATA_FLOWS)}  trust boundaries: {len(TRUST_BOUNDARIES)}")
    print("  untrusted input enters at:")
    for p in untrusted_entry_points():
        print(f"    - {p['flow']}: {p['from']} -> {p['to']}  ({p['data']})")
