# Lab 3 - Build a CLI triage tool (CPU only, no GPU)

Full step-by-step instructions with expected output are in **Module3_Learner_Guide.docx (Part B)**.

**Two tracks, same lesson:**
- **Track A - Walkthrough (no terminal):** open `../simulations/sim6_lab3_cli_walkthrough.html` in a browser on your
  Windows laptop. Nothing to install. You do not need this folder.
- **Track B - Hands-on:** use this folder on your **Module 0 VM in OCI** (same VM as Labs 1 and 2).

## Setup (Track B)
Nothing to install on your Windows laptop: `ssh` and `scp` are built into Windows 10 and 11.

1. On your Windows laptop, open **Command Prompt** (Windows key, type `cmd`, Enter) and go to the folder where you
   unzipped the package:
```
cd "C:\Users\<you>\Downloads\Module3"
scp -r lab3 <user>@<vm-address>:~/
ssh -o ServerAliveInterval=30 <user>@<vm-address>
```
   Replace `<user>` and `<vm-address>` with your Module 0 values, including the `<` and `>`.
   `ServerAliveInterval=30` keeps the connection open while the CPU is thinking.
   Using an SSH key file? Add `-i "C:\path\to\key"` to both commands.

2. On the VM:
```
cd ~/lab3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_setup.py
```
`check_setup.py` must end with `All required checks passed.` If you log in again later, first run
`cd ~/lab3` and `source .venv/bin/activate`.

## What you run (no code editing needed)
| Part | Command | AI? |
|---|---|---|
| 1 Messages and roles | `curl` with `requests/01` to `04` (command below) | yes |
| 2 System prompt | `python step2_system_prompt.py` | yes |
| 3 Structured output | `python step3_structured.py --examples` then `python step3_structured.py` | no, then yes |
| 4 Tokens and cost | `python step4_tokens.py --offline` then `python step4_tokens.py` | no, then yes |
| 5 Security | `python step5_security.py` | no |
| 6 The CLI tool | `python triage.py alerts/a1_ssh_bruteforce.txt` (and a2, a3, a4, `--dry-run`, `--json`) | yes |
| 7 Prove it | `python -m pytest -v` and `python -m bandit triage.py llm.py safety.py schema.py` | no |

Part 1 command (then the same with 02, 03 and 04):
```
curl -s --noproxy '*' http://127.0.0.1:11434/api/chat -d @requests/01_one_message.json | python3 -m json.tool
```

Each AI call takes about 30 seconds to 2 minutes on a CPU. That is normal.

## Files
| File | Purpose |
|---|---|
| `triage.py` | The finished CLI tool: reads an alert, redacts, asks the AI for JSON, validates, applies policy |
| `llm.py` | Tiny client for the local Ollama API (standard library only) |
| `safety.py` | Redaction, prompt-injection detection, tag wrapping, output cleaning |
| `schema.py` | The JSON contract for the AI's answer, and the validator |
| `prompts/` | System prompts (`system_rules.txt` for Part 2, `system_triage.txt` for the tool) |
| `requests/` | Ready-made JSON requests for `curl` in Part 1 |
| `alerts/` | Four fake alerts: SOC (a1, a3), DevOps (a2), IT Operations (a4) |
| `step2` to `step5` | One small script per section |
| `tests/` | 30 tests that run without the AI (a fake AI stands in) |
| `prices.example.json` | EXAMPLE token prices for the cost maths - not real prices |
| `check_setup.py` | Tells you exactly what is missing |

## Exit codes of triage.py
`0` = triaged, no human needed | `2` = a human must review | `1` = error (input or Ollama).
A human must review when the input contained secrets or personal data (they are redacted, but the leak is
real), the severity is high or critical, the AI recommends a `_request` action, the alert contains
prompt-injection text, the AI says `needs_more_data`, or the AI answer was invalid twice.

## Safety
All data is fake (documentation IP ranges, example keys). The AI only recommends; the tool never blocks,
isolates or deletes anything. Follow the Module 1 rules at work: never paste real secrets or personal data
into an AI tool, use approved tools only.
