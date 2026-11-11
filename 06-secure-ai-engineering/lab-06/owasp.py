"""
owasp.py - the OWASP LLM Top 10 (2025), with, for each risk:
  - a plain-words description,
  - how THIS system (the SOC triage agent) is exposed,
  - which of our controls address it (looked up from controls.py).

This is the "are we covered?" table a CISO asks for first.
"""
import controls

# (id, title, plain description, how this system is exposed)
TOP10 = [
    ("LLM01", "Prompt injection",
     "Hostile instructions hidden in content the model reads, aiming to redirect its behaviour.",
     "A ticket comment written by an outsider tries to make the agent disable an account and email data out."),
    ("LLM02", "Sensitive information disclosure",
     "The model reveals private data it was given or can reach.",
     "The agent reads auth logs and CMDB data; a hijack could try to exfiltrate them."),
    ("LLM03", "Supply chain",
     "Risk from the model, libraries, tools or data sources you depend on.",
     "Open-weight model and tools; we pin versions and host locally rather than call a third-party API."),
    ("LLM04", "Data and model poisoning",
     "Tampered training or reference data that corrupts behaviour.",
     "We do not train or fine-tune; the model is read-only and fixed, and reference data is internal and reviewed."),
    ("LLM05", "Improper output handling",
     "Trusting model or tool output and acting on it without checking.",
     "A tool result could contain markup or instructions; acting on it blindly would be unsafe."),
    ("LLM06", "Excessive agency",
     "Giving the model too many tools, too much permission, or too much autonomy.",
     "The agent can call tools that disable accounts or email out - far more power than triage needs."),
    ("LLM07", "System prompt leakage",
     "Secrets placed in the system prompt that can be extracted.",
     "Our system prompt holds no secrets or credentials - only behavioural rules."),
    ("LLM08", "Vector and embedding weaknesses",
     "Attacks on a retrieval/embedding store (e.g. poisoned chunks).",
     "This agent uses no vector store (that was Module 4); not applicable here, noted for completeness."),
    ("LLM09", "Misinformation",
     "The model states something false with confidence.",
     "The agent could mis-rate an alert; a human approves every action and a deterministic path exists."),
    ("LLM10", "Unbounded consumption",
     "Runaway loops or huge inputs exhausting resources or budget.",
     "An agent loop with no limit could call tools forever, a denial-of-service on the VM."),
]


def coverage():
    """For each OWASP risk, the controls that address it (or 'N/A - <why>')."""
    rows = []
    for oid, title, desc, exposure in TOP10:
        ctls = controls.controls_for_owasp(oid)
        rows.append({"id": oid, "title": title, "desc": desc, "exposure": exposure, "controls": ctls})
    return rows


def gaps():
    """OWASP risks with no mapped control (expected: the genuinely not-applicable ones)."""
    return [r["id"] for r in coverage() if not r["controls"]]


if __name__ == "__main__":
    for r in coverage():
        tag = ", ".join(r["controls"]) if r["controls"] else "N/A (see notes)"
        print(f"  {r['id']}  {r['title']:34s} -> {tag}")
    print("\nNo mapped control (by design, not applicable):", gaps() or "none")
