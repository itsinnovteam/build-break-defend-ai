# Lab 5 - Build an agent, then hijack it (CPU only, open source)

Full step-by-step instructions, expected outputs and explanations are in
**Module5_Learner_Guide.docx, chapter 7**. This file is the quick reference.

**Two tracks, same lesson**
- **Track A - walkthrough (no terminal):** open `../simulations/sim5_lab5_walkthrough.html` in a browser.
- **Track B - hands-on:** this folder, on your **Module 0 VM** (Oracle Linux 9, Python 3.9, Ollama). No GPU.

## Stack
| Component | Used for | License |
|---|---|---|
| Ollama + `llama3.1:8b` | the model (supports tool calling) | MIT / Llama 3.1 Community License |
| Python 3.9 standard library | all lab code, the agent loop, the tools, the MCP server | PSF |
| pytest 8.4.2, bandit 1.8.6 | tests and scan (Phase 6 only) | MIT, Apache 2.0 |

No third-party packages are needed to run the agent. The tools act on local files under
`state/`, never on real systems or the network. All data is fake.

## Phase 1 - Setup
Windows laptop, **Command Prompt** (nothing to install; no PowerShell):
```
cd "%USERPROFILE%\Downloads\Module5"
scp -r lab5 <user>@<vm-address>:~/
ssh -o ServerAliveInterval=30 <user>@<vm-address>
```
On the VM:
```
cd ~/lab5
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_setup.py
```
`check_setup.py` must end with `All required checks passed.` After every new login:
`cd ~/lab5` and `source .venv/bin/activate`. llama3.1:8b is already on the VM from Module 0.

## What you run (no code editing)
| Phase | Commands | AI? |
|---|---|---|
| 1 Setup | `python check_setup.py` | one check call |
| 2 Tools and MCP | `python tool_demo.py`, `python mcp_client.py` | demo, then no |
| 3 Build the agent | `python run_agent.py --task "Triage alert A-1008"` | yes |
| 4 When not to use agents | `python plain_vs_agent.py` | no |
| 5 Break it (v1) | `python run_agent.py --task "Triage alert A-1007" --version v1` | yes |
| 6 Secure it (v2) | `python run_agent.py --task "Triage alert A-1007"` (defended, the default) | yes |
| 7 Verify | `python attacks.py`, `python -m pytest -v`, `python -m bandit -r . -x ./tests,./.venv` | no |

Each AI step takes about 10 to 60 seconds on a CPU. `attacks.py` and the tests use a scripted
model (a stand-in for a fully hijacked model), so they need no AI and run in seconds.

**Pass conditions:** `attacks.py` -> v1 stopped 0 of 1, v2 stopped 1 of 1 · `pytest` -> 24 passed ·
`bandit` -> No issues identified.

## The idea in one line
The MODEL only ever RETURNS a request to call a tool. **Our code decides whether it runs.**
That decision point (`handle_call` in `agent.py`) is the whole security story.

## The two agents
- **v1 (naive):** every tool available, tool output trusted, no approval -> hijacked by a poisoned alert.
- **v2 (defended):** five layers in code:
  1. **Least privilege** - the triage agent is given only read-only tools + `add_case_note`.
  2. **Human approval** - any production-changing or external action waits for a person.
  3. **Argument checks** - even an approved action is validated (no disabling critical accounts, no external email, no blocking internal IPs).
  4. **Output is data** - every tool result is wrapped in `<observation>` and never executed.
  5. **Limits + audit** - step and tool-call limits stop runaways; `agent_audit.log` records every call (no secrets).

The "lethal trifecta": an agent that can (1) read private data, (2) see untrusted content and
(3) talk to the outside world can be made to exfiltrate. v2 breaks it by not giving the triage
agent any external tool at all.

## Files
| File | Purpose |
|---|---|
| `toolkit.py` | the SOC tools, each with a schema and a risk level (read / write / extern) |
| `agent.py` | the agent loop and `handle_call` (the trust boundary); Policy.naive / Policy.defended |
| `ollama_client.py` | tool-calling client for the local Ollama API (stdlib) |
| `mcp_server.py` / `mcp_client.py` | a tiny MCP (Model Context Protocol) server and client over stdio |
| `run_agent.py` | run the agent (v1 or v2) on an alert |
| `tool_demo.py` | one tool-calling round trip, shown in full |
| `plain_vs_agent.py` | when NOT to use an agent (a plain script vs the agent) |
| `attacks.py` | hijack v1 vs v2, and the four defences one bad call each |
| `scenarios/` | synthetic SOC alerts; A-1007 has a poisoned comment |
| `prompts/` | system prompts for v1 and v2 |
| `safety.py` | injection detection, output tagging (from Labs 2 to 4) |
| `scripted_model.py` | a stand-in for a fully hijacked model (tests and attacks) |
| `tests/test_lab5.py` | 24 tests, no Ollama needed |

## Safety
All data is fake; tools touch only local files under `state/`. Run the hijack only against this
lab on your own VM. At work, follow the Module 1 rules and never give an agent real tools without
the controls in this lab.
