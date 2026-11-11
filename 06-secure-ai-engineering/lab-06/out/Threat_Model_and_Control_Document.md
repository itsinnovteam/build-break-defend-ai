# Threat Model & Control Document
**System:** SOC Triage Agent (1.0 (Lab 5, defended / v2))  
**Owner:** Security Operations / Innovation Team  
**Date:** 2026-10-25  
**Hosting:** Self-hosted on an internal VM (Oracle Linux 9). Local open-weight model via Ollama. No data leaves the network.

> Prepared for security review. Every control in this document is backed by an automated test in Lab 5 (see the Evidence column). Compliance clause references are representative; map them to your own framework as needed.

## 1. Purpose and scope
Investigate a SOC alert using read-only tools and recommend an action for a human to approve.

This document threat-models the agent, maps it to the OWASP LLM Top 10 and common compliance frameworks, records the deployment decision, and lists the controls with their evidence.

## 2. Data flow and trust boundaries
**Components**

| ID | Component | Zone | Role |
|----|-----------|------|------|
| C1 | Operator / analyst | internal | The human who starts a triage and approves risky actions. |
| C2 | Agent loop (agent.py) | internal | Orchestrates think-act-observe; calls the trust boundary for every tool. |
| C3 | Trust boundary (handle_call) | internal | The one function that allows, denies or validates every tool call. |
| C4 | Local LLM (llama3.1:8b via Ollama) | model | Proposes tool calls and writes the final answer. Untrusted decision-maker. |
| C5 | Tools (toolkit.py) + MCP server | internal | The 8 SOC tools; the MCP server exposes only the read-only ones. |
| C6 | Local state (state/, audit log) | internal | Case notes, blocklist, outbox and the audit log - local files only. |
| C7 | Alert + ticket data (scenarios/) | internal | SOC alerts. Ticket COMMENTS may be written by outsiders - untrusted content. |

**Data flows**

| Flow | From | To | Data | Untrusted? |
|------|------|----|------|-----------|
| F1 | Operator / analyst | Agent loop (agent.py) | Triage task (which alert) | no |
| F2 | Agent loop (agent.py) | Local LLM (llama3.1:8b via Ollama) | Task + tool menu + observations so far | no |
| F3 | Local LLM (llama3.1:8b via Ollama) | Agent loop (agent.py) | A proposed tool call (name + arguments) | YES |
| F4 | Agent loop (agent.py) | Trust boundary (handle_call) | The proposed tool call, for a decision | YES |
| F5 | Trust boundary (handle_call) | Tools (toolkit.py) + MCP server | An allowed tool call | no |
| F6 | Tools (toolkit.py) + MCP server | Alert + ticket data (scenarios/) | Reads alert + ticket comments | no |
| F7 | Alert + ticket data (scenarios/) | Agent loop (agent.py) | Tool result incl. outsider-written comment | YES |
| F8 | Tools (toolkit.py) + MCP server | Local state (state/, audit log) | Writes case note / blocklist / audit entry | no |
| F9 | Trust boundary (handle_call) | Operator / analyst | Approval request for a write/external action | no |

**Trust boundaries**

- **TB1 Model boundary** (crosses F3, F4): The LLM is untrusted: anything it proposes (F3) is a REQUEST, never an order. handle_call (C3) is the gate.
- **TB2 Untrusted-content boundary** (crosses F7): Ticket comments can be written by outsiders. They arrive as tool results (F7) and must be treated as DATA, never instructions.
- **TB3 Action boundary** (crosses F5, F8, F9): Any action that changes state or reaches outside needs least privilege, argument checks and (for write/extern) human approval.

**Where untrusted input enters** (the first question to answer):

- `F3` Local LLM (llama3.1:8b via Ollama) -> Agent loop (agent.py) - A proposed tool call (name + arguments)
- `F4` Agent loop (agent.py) -> Trust boundary (handle_call) - The proposed tool call, for a decision
- `F7` Alert + ticket data (scenarios/) -> Agent loop (agent.py) - Tool result incl. outsider-written comment

## 3. Threat model (STRIDE over the boundaries)
11 threats identified: **9 mitigated**, 2 not applicable, **0 open**.

| Threat | STRIDE | Target | Description | Decision | Control |
|--------|--------|--------|-------------|----------|---------|
| T1 | Tampering/Elevation | TB1 model boundary (F3) | The model is tricked into proposing a dangerous tool call (disable account, email out). | Mitigated | CTL-01 |
| T2 | Elevation | TB2 untrusted content (F7) | A ticket comment carries injected instructions that the agent might obey. | Mitigated | CTL-04 |
| T3 | Information disclosure | TB2 -> outside | Private logs/CMDB are exfiltrated to an external address via a tool. | Mitigated | CTL-08 |
| T4 | Elevation | TB3 action boundary (F5) | A write or external action runs without a human decision. | Mitigated | CTL-02 |
| T5 | Tampering | TB3 action boundary (F5) | An approved action is aimed at the wrong target (critical account, internal IP). | Mitigated | CTL-03 |
| T6 | Denial of service | C2 agent loop | A runaway or hijacked loop calls tools endlessly and exhausts the VM. | Mitigated | CTL-05 |
| T7 | Repudiation | C6 state + audit | An action happens with no record of who/what/when, so it cannot be reviewed. | Mitigated | CTL-06 |
| T8 | Elevation | C5 MCP server | A dangerous tool is reached through the MCP server directly. | Mitigated | CTL-07 |
| T9 | Information disclosure | C4 model + data | Data leaves the network by being sent to a third-party model API. | Mitigated | CTL-09 |
| T10 | Tampering | C4 model supply chain | The model is poisoned via training/fine-tuning data. | Not applicable | - |
| T11 | Information disclosure | system prompt | Secrets are extracted from the system prompt. | Not applicable | - |

## 4. OWASP LLM Top 10 (2025) coverage
| ID | Risk | How this system is exposed | Controls |
|----|------|----------------------------|----------|
| LLM01 | Prompt injection | A ticket comment written by an outsider tries to make the agent disable an account and email data out. | CTL-01, CTL-04, CTL-08, CTL-10 |
| LLM02 | Sensitive information disclosure | The agent reads auth logs and CMDB data; a hijack could try to exfiltrate them. | CTL-06, CTL-08, CTL-09 |
| LLM03 | Supply chain | Open-weight model and tools; we pin versions and host locally rather than call a third-party API. | CTL-07, CTL-09 |
| LLM04 | Data and model poisoning | We do not train or fine-tune; the model is read-only and fixed, and reference data is internal and reviewed. | N/A by design |
| LLM05 | Improper output handling | A tool result could contain markup or instructions; acting on it blindly would be unsafe. | CTL-03, CTL-04 |
| LLM06 | Excessive agency | The agent can call tools that disable accounts or email out - far more power than triage needs. | CTL-01, CTL-02, CTL-03, CTL-07 |
| LLM07 | System prompt leakage | Our system prompt holds no secrets or credentials - only behavioural rules. | N/A by design |
| LLM08 | Vector and embedding weaknesses | This agent uses no vector store (that was Module 4); not applicable here, noted for completeness. | N/A by design |
| LLM09 | Misinformation | The agent could mis-rate an alert; a human approves every action and a deterministic path exists. | CTL-10 |
| LLM10 | Unbounded consumption | An agent loop with no limit could call tools forever, a denial-of-service on the VM. | CTL-05 |

Risks marked *N/A by design*: LLM04, LLM07, LLM08 - documented with rationale in the threat model (not unmanaged gaps).

## 5. Controls and evidence
Each control names the Lab 5 test that proves it works. Run `python link_lab5.py` to execute them live.

### CTL-01 - Least privilege (tool allowlist)
- **What:** The agent may use only the tools its job needs. The triage job gets read-only tools plus add_case_note; nothing else can run.
- **Mechanism:** `handle_call rejects any tool not in policy.allowlist (config.TRIAGE_ALLOWLIST).`
- **OWASP:** LLM06, LLM01
- **Compliance:** NIST AI RMF MANAGE-2.2; ISO 42001 A.6.2.4; ISO 27001 A.8.2 (privileged access); SOC 2 CC6.1 / CC6.3
- **Evidence (tests):** `test_triage_policy_blocks_tools_outside_the_allowlist`, `test_v2_never_runs_a_forbidden_tool_whatever_the_model_asks`

### CTL-02 - Human approval for impactful actions
- **What:** Any action that changes production or leaves the building waits for a person to approve before it runs.
- **Mechanism:** `handle_call denies WRITE/EXTERN tools unless policy.approve() returns True (add_case_note is the only auto-allowed write).`
- **OWASP:** LLM06
- **Compliance:** NIST AI RMF MANAGE-1.3; ISO 42001 A.9.2 (human oversight); ISO 27001 A.5.3; SOC 2 CC6.1
- **Evidence (tests):** `test_write_tool_needs_approval`, `test_case_note_needs_no_approval`

### CTL-03 - Argument validation
- **What:** Even an approved action is checked: no disabling critical accounts, no external email, no blocking internal IPs.
- **Mechanism:** `default_validate() runs inside handle_call before any tool executes.`
- **OWASP:** LLM06, LLM05
- **Compliance:** NIST AI RMF MEASURE-2.6; ISO 42001 A.6.2.4; ISO 27001 A.8.28 (secure coding); SOC 2 CC8.1
- **Evidence (tests):** `test_argument_check_refuses_disabling_a_critical_account`, `test_argument_check_refuses_external_email`, `test_argument_check_refuses_blocking_an_internal_ip`

### CTL-04 - Output handled as data, not orders
- **What:** Every tool result is wrapped in <observation> and treated as data to read, never as instructions. Injection attempts are detected and flagged.
- **Mechanism:** `safety.wrap_observation() and safety.find_injection() applied to every observation in the defended agent.`
- **OWASP:** LLM01, LLM05
- **Compliance:** NIST AI RMF MEASURE-2.7; ISO 42001 A.6.2.4; ISO 27001 A.8.28 (secure coding); SOC 2 CC6.8
- **Evidence (tests):** `test_v2_wraps_tool_output_as_data`, `test_injection_is_detected_in_the_poisoned_alert`, `test_defused_tag_cannot_break_out_of_observation`

### CTL-05 - Loop limits (no runaway)
- **What:** Hard caps on steps and total tool calls stop a buggy or hijacked loop from running forever.
- **Mechanism:** `config.MAX_STEPS and config.MAX_TOOL_CALLS enforced in agent.run().`
- **OWASP:** LLM10
- **Compliance:** NIST AI RMF MANAGE-2.2; ISO 42001 A.6.2.6; ISO 27001 A.8.6 (capacity); SOC 2 A1.1
- **Evidence (tests):** `test_step_limit_stops_a_runaway_loop`, `test_tool_call_limit_is_enforced`

### CTL-06 - Audit logging without secrets
- **What:** Every tool call is recorded - tool, risk, decision - with no arguments or results, so the log itself leaks nothing.
- **Mechanism:** `agent.write_audit() writes agent_audit.log with metadata only.`
- **OWASP:** LLM02
- **Compliance:** NIST AI RMF MEASURE-2.8; ISO 42001 A.6.2.8; ISO 27001 A.8.15 (logging); SOC 2 CC7.2
- **Evidence (tests):** `test_audit_has_no_argument_or_result_text`

### CTL-07 - Least privilege at the server (MCP)
- **What:** The MCP server exposes only the four read-only tools. The dangerous tools are unreachable through it.
- **Mechanism:** `mcp_server.py READ_ONLY allowlist; refuses tools/call for anything else.`
- **OWASP:** LLM06, LLM03
- **Compliance:** NIST AI RMF MANAGE-2.2; ISO 42001 A.6.2.4; ISO 27001 A.8.2 (privileged access); SOC 2 CC6.3
- **Evidence (tests):** `test_mcp_server_exposes_only_read_only_tools`, `test_mcp_server_refuses_a_tool_it_does_not_expose`

### CTL-08 - Break the lethal trifecta
- **What:** The triage agent has no external tool at all, so private data can never be exfiltrated even if the model is hijacked.
- **Mechanism:** `send_email is not in TRIAGE_ALLOWLIST; the exfiltration leg is removed by design.`
- **OWASP:** LLM02, LLM01
- **Compliance:** NIST AI RMF MAP-2.1; ISO 42001 A.5.2 (risk assessment); ISO 27001 A.8.12 (data leakage prevention); SOC 2 CC6.7
- **Evidence (tests):** `test_v2_blocks_the_hijack_but_still_triages`

### CTL-09 - Local hosting / data residency
- **What:** The model and all data stay on an internal VM. No alert, log or PII is sent to any outside service.
- **Mechanism:** `Ollama local model; tools act only on local files under state/; email domain allowlist is internal-only.`
- **OWASP:** LLM02, LLM03
- **Compliance:** NIST AI RMF GOVERN-1.2; ISO 42001 A.7.2 (data management); ISO 27001 A.5.34 (privacy); SOC 2 C1.1 / P4.1
- **Evidence (tests):** `test_argument_check_refuses_external_email`

### CTL-10 - Prefer the deterministic path
- **What:** When the steps are fixed, a plain script (no model) does the job - no injection surface at all.
- **Mechanism:** `plain_vs_agent.py performs triage with zero model calls, deterministically.`
- **OWASP:** LLM01, LLM09
- **Compliance:** NIST AI RMF MAP-1.1; ISO 42001 A.6.1.2; ISO 27001 A.8.25; SOC 2 CC8.1
- **Evidence (tests):** `test_plain_triage_is_deterministic_and_uses_no_model`

## 6. Deployment pattern decision
The most sensitive data handled is **confidential**. Recommended pattern: **P4 Fully local / on-prem open-weight model (this lab)**.

> Confidential or regulated data that must not leave the network. Trade-off: You run and patch it; capacity is your own - the trade for full control.

| Pattern | Control over data | Up to sensitivity | Good for |
|---------|-------------------|-------------------|----------|
| P4 Fully local / on-prem open-weight model (this lab) | highest | regulated | Confidential or regulated data that must not leave the network. |
| P3 Private cloud / VPC-hosted open model | high | confidential | Confidential data that may live in your cloud tenancy. |
| P2 Vendor API with data-protection contract (no training, region-locked) | medium | internal | Internal content where a contract and region lock are acceptable. |
| P1 Public SaaS LLM API | low | public | Public, non-sensitive content; prototypes. |

## 7. Compliance mapping
### NIST AI RMF
*US AI Risk Management Framework - functions GOVERN / MAP / MEASURE / MANAGE.* - 8 clauses touched.

| Clause | Controls | Evidence tests |
|--------|----------|----------------|
| GOVERN-1.2 | CTL-09 | 1 |
| MANAGE-1.3 | CTL-02 | 2 |
| MANAGE-2.2 | CTL-01, CTL-05, CTL-07 | 6 |
| MAP-1.1 | CTL-10 | 1 |
| MAP-2.1 | CTL-08 | 1 |
| MEASURE-2.6 | CTL-03 | 3 |
| MEASURE-2.7 | CTL-04 | 3 |
| MEASURE-2.8 | CTL-06 | 1 |

### ISO 42001
*AI Management System standard - Annex A controls for responsible AI.* - 7 clauses touched.

| Clause | Controls | Evidence tests |
|--------|----------|----------------|
| A.5.2 (risk assessment) | CTL-08 | 1 |
| A.6.1.2 | CTL-10 | 1 |
| A.6.2.4 | CTL-01, CTL-03, CTL-04, CTL-07 | 10 |
| A.6.2.6 | CTL-05 | 2 |
| A.6.2.8 | CTL-06 | 1 |
| A.7.2 (data management) | CTL-09 | 1 |
| A.9.2 (human oversight) | CTL-02 | 2 |

### ISO 27001
*Information security management - Annex A controls.* - 8 clauses touched.

| Clause | Controls | Evidence tests |
|--------|----------|----------------|
| A.5.3 | CTL-02 | 2 |
| A.5.34 (privacy) | CTL-09 | 1 |
| A.8.12 (data leakage prevention) | CTL-08 | 1 |
| A.8.15 (logging) | CTL-06 | 1 |
| A.8.2 (privileged access) | CTL-01, CTL-07 | 4 |
| A.8.25 | CTL-10 | 1 |
| A.8.28 (secure coding) | CTL-03, CTL-04 | 6 |
| A.8.6 (capacity) | CTL-05 | 2 |

### SOC 2
*Trust Services Criteria (Security, Availability, Confidentiality, Privacy).* - 9 clauses touched.

| Clause | Controls | Evidence tests |
|--------|----------|----------------|
| A1.1 | CTL-05 | 2 |
| C1.1 / P4.1 | CTL-09 | 1 |
| CC6.1 | CTL-02 | 2 |
| CC6.1 / CC6.3 | CTL-01 | 2 |
| CC6.3 | CTL-07 | 2 |
| CC6.7 | CTL-08 | 1 |
| CC6.8 | CTL-04 | 3 |
| CC7.2 | CTL-06 | 1 |
| CC8.1 | CTL-03, CTL-10 | 4 |

## 8. Data governance
| Data asset | Sensitivity | PII | Residency |
|------------|-------------|-----|-----------|
| Alert metadata | internal | no | on-VM |
| Authentication logs | confidential | yes | on-VM |
| Asset owner / CMDB | confidential | yes | on-VM |
| Ticket comments (may be outsider-written) | untrusted-input | no | on-VM |
| Case notes + audit log | confidential | no | on-VM |

All data stays on the VM (residency: on-VM). No asset is sent to any external service.

## 9. Residual risk and sign-off
- Threats: 9 mitigated, 2 not applicable, **0 open**.
- Accepted / not-applicable items carry a documented rationale (see section 3).
- Residual risk: the local model can still mis-rate an alert (LLM09); mitigated by mandatory human approval for any action and by the deterministic fallback path.

| Role | Name | Decision | Date |
|------|------|----------|------|
| System owner | ______________ | ______________ | ______ |
| Security reviewer / CISO | ______________ | Approve / Reject | ______ |
