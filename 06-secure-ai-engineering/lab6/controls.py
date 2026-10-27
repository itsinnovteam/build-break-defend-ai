"""
controls.py - the control catalogue for the SOC Triage Agent.

Each control lists:
  - what it is and the exact mechanism in the Lab 5 code,
  - which OWASP LLM Top 10 risks it addresses,
  - which compliance clauses it helps satisfy,
  - EVIDENCE: the Lab 5 test that proves it actually works.

The evidence test ids are real tests in Lab 5 (tests/test_lab5.py). That is what
makes this document defendable: every control is backed by a passing test, not a
promise. link_lab5.py can run them live when the lab5 folder is next to this one.
"""

# Compliance framework clause references are representative and widely recognised.
# Swap them for your own framework's clause numbers - the mapping method is the point.
CONTROLS = [
    {
        "id": "CTL-01", "name": "Least privilege (tool allowlist)",
        "what": "The agent may use only the tools its job needs. The triage job gets read-only tools plus add_case_note; nothing else can run.",
        "mechanism": "handle_call rejects any tool not in policy.allowlist (config.TRIAGE_ALLOWLIST).",
        "owasp": ["LLM06", "LLM01"],
        "compliance": {"NIST AI RMF": "MANAGE-2.2", "ISO 42001": "A.6.2.4", "ISO 27001": "A.8.2 (privileged access)", "SOC 2": "CC6.1 / CC6.3"},
        "evidence": ["test_triage_policy_blocks_tools_outside_the_allowlist", "test_v2_never_runs_a_forbidden_tool_whatever_the_model_asks"],
    },
    {
        "id": "CTL-02", "name": "Human approval for impactful actions",
        "what": "Any action that changes production or leaves the building waits for a person to approve before it runs.",
        "mechanism": "handle_call denies WRITE/EXTERN tools unless policy.approve() returns True (add_case_note is the only auto-allowed write).",
        "owasp": ["LLM06"],
        "compliance": {"NIST AI RMF": "MANAGE-1.3", "ISO 42001": "A.9.2 (human oversight)", "ISO 27001": "A.5.3", "SOC 2": "CC6.1"},
        "evidence": ["test_write_tool_needs_approval", "test_case_note_needs_no_approval"],
    },
    {
        "id": "CTL-03", "name": "Argument validation",
        "what": "Even an approved action is checked: no disabling critical accounts, no external email, no blocking internal IPs.",
        "mechanism": "default_validate() runs inside handle_call before any tool executes.",
        "owasp": ["LLM06", "LLM05"],
        "compliance": {"NIST AI RMF": "MEASURE-2.6", "ISO 42001": "A.6.2.4", "ISO 27001": "A.8.28 (secure coding)", "SOC 2": "CC8.1"},
        "evidence": ["test_argument_check_refuses_disabling_a_critical_account", "test_argument_check_refuses_external_email", "test_argument_check_refuses_blocking_an_internal_ip"],
    },
    {
        "id": "CTL-04", "name": "Output handled as data, not orders",
        "what": "Every tool result is wrapped in <observation> and treated as data to read, never as instructions. Injection attempts are detected and flagged.",
        "mechanism": "safety.wrap_observation() and safety.find_injection() applied to every observation in the defended agent.",
        "owasp": ["LLM01", "LLM05"],
        "compliance": {"NIST AI RMF": "MEASURE-2.7", "ISO 42001": "A.6.2.4", "ISO 27001": "A.8.28 (secure coding)", "SOC 2": "CC6.8"},
        "evidence": ["test_v2_wraps_tool_output_as_data", "test_injection_is_detected_in_the_poisoned_alert", "test_defused_tag_cannot_break_out_of_observation"],
    },
    {
        "id": "CTL-05", "name": "Loop limits (no runaway)",
        "what": "Hard caps on steps and total tool calls stop a buggy or hijacked loop from running forever.",
        "mechanism": "config.MAX_STEPS and config.MAX_TOOL_CALLS enforced in agent.run().",
        "owasp": ["LLM10"],
        "compliance": {"NIST AI RMF": "MANAGE-2.2", "ISO 42001": "A.6.2.6", "ISO 27001": "A.8.6 (capacity)", "SOC 2": "A1.1"},
        "evidence": ["test_step_limit_stops_a_runaway_loop", "test_tool_call_limit_is_enforced"],
    },
    {
        "id": "CTL-06", "name": "Audit logging without secrets",
        "what": "Every tool call is recorded - tool, risk, decision - with no arguments or results, so the log itself leaks nothing.",
        "mechanism": "agent.write_audit() writes agent_audit.log with metadata only.",
        "owasp": ["LLM02"],
        "compliance": {"NIST AI RMF": "MEASURE-2.8", "ISO 42001": "A.6.2.8", "ISO 27001": "A.8.15 (logging)", "SOC 2": "CC7.2"},
        "evidence": ["test_audit_has_no_argument_or_result_text"],
    },
    {
        "id": "CTL-07", "name": "Least privilege at the server (MCP)",
        "what": "The MCP server exposes only the four read-only tools. The dangerous tools are unreachable through it.",
        "mechanism": "mcp_server.py READ_ONLY allowlist; refuses tools/call for anything else.",
        "owasp": ["LLM06", "LLM03"],
        "compliance": {"NIST AI RMF": "MANAGE-2.2", "ISO 42001": "A.6.2.4", "ISO 27001": "A.8.2 (privileged access)", "SOC 2": "CC6.3"},
        "evidence": ["test_mcp_server_exposes_only_read_only_tools", "test_mcp_server_refuses_a_tool_it_does_not_expose"],
    },
    {
        "id": "CTL-08", "name": "Break the lethal trifecta",
        "what": "The triage agent has no external tool at all, so private data can never be exfiltrated even if the model is hijacked.",
        "mechanism": "send_email is not in TRIAGE_ALLOWLIST; the exfiltration leg is removed by design.",
        "owasp": ["LLM02", "LLM01"],
        "compliance": {"NIST AI RMF": "MAP-2.1", "ISO 42001": "A.5.2 (risk assessment)", "ISO 27001": "A.8.12 (data leakage prevention)", "SOC 2": "CC6.7"},
        "evidence": ["test_v2_blocks_the_hijack_but_still_triages"],
    },
    {
        "id": "CTL-09", "name": "Local hosting / data residency",
        "what": "The model and all data stay on an internal VM. No alert, log or PII is sent to any outside service.",
        "mechanism": "Ollama local model; tools act only on local files under state/; email domain allowlist is internal-only.",
        "owasp": ["LLM02", "LLM03"],
        "compliance": {"NIST AI RMF": "GOVERN-1.2", "ISO 42001": "A.7.2 (data management)", "ISO 27001": "A.5.34 (privacy)", "SOC 2": "C1.1 / P4.1"},
        "evidence": ["test_argument_check_refuses_external_email"],
    },
    {
        "id": "CTL-10", "name": "Prefer the deterministic path",
        "what": "When the steps are fixed, a plain script (no model) does the job - no injection surface at all.",
        "mechanism": "plain_vs_agent.py performs triage with zero model calls, deterministically.",
        "owasp": ["LLM01", "LLM09"],
        "compliance": {"NIST AI RMF": "MAP-1.1", "ISO 42001": "A.6.1.2", "ISO 27001": "A.8.25", "SOC 2": "CC8.1"},
        "evidence": ["test_plain_triage_is_deterministic_and_uses_no_model"],
    },
]


def by_id(cid):
    for c in CONTROLS:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def controls_for_owasp(owasp_id):
    return [c["id"] for c in CONTROLS if owasp_id in c["owasp"]]


def all_evidence_tests():
    tests = []
    for c in CONTROLS:
        tests.extend(c["evidence"])
    return sorted(set(tests))


if __name__ == "__main__":
    print(f"{len(CONTROLS)} controls, {len(all_evidence_tests())} distinct evidence tests")
    for c in CONTROLS:
        print(f"  {c['id']}  {c['name']:38s}  OWASP {','.join(c['owasp'])}")
