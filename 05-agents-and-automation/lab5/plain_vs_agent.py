"""
plain_vs_agent.py - Section 5.4: when NOT to use an agent.

Some jobs are a FIXED sequence of steps. For those a plain script is cheaper, faster,
repeatable and far easier to secure than an agent - because there is no model deciding what
to do at run time, so there is nothing to hijack.

This runs the SAME triage two ways and compares them:
  plain_triage()  a normal function: always the same 3 steps, 0 model calls
  the agent       a model decides the steps at run time (Lab 5)

Run:  python plain_vs_agent.py        (no Ollama needed: the plain path uses no model)
"""

import toolkit


def plain_triage(alert_id):
    """A fixed recipe. No model. The same steps every time, so nothing to hijack."""
    alert = toolkit.get_alert(alert_id)
    rep = toolkit.lookup_ip_reputation(alert["source_ip"])
    toolkit.add_case_note(alert_id, f"Auto-triage: source IP {alert['source_ip']} is {rep['verdict']}.")
    recommend = "block IP + reset password" if rep["verdict"] == "malicious" else "monitor"
    return {"alert": alert_id, "verdict": rep["verdict"], "recommend": recommend,
            "model_calls": 0, "tool_calls": 3, "deterministic": True}


def main():
    result = plain_triage("A-1007")
    print("PLAIN SCRIPT (no agent):")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("\n  Same result every run. No model, so no prompt-injection risk. Easy to test.\n")

    print("WHEN A PLAIN SCRIPT IS THE RIGHT CHOICE")
    for line in [
        "- The steps are fixed and known in advance (this triage recipe).",
        "- The task runs often, or must be cheap, fast and 100% repeatable.",
        "- A wrong action would be costly, and you want zero run-time surprises.",
        "- You cannot afford the attack surface an agent adds.",
    ]:
        print("  " + line)
    print("\nWHEN AN AGENT EARNS ITS RISK")
    for line in [
        "- The steps are NOT known ahead of time and depend on what each tool returns.",
        "- A human would otherwise improvise across many tools (open-ended investigation).",
        "- The flexibility is worth the extra cost, latency and the security work in Lab 5.",
    ]:
        print("  " + line)
    print("\nRule of thumb: reach for a script or a RAG lookup first (Modules 3 and 4). Use an")
    print("agent only when the task really needs to decide its own steps - then secure it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
