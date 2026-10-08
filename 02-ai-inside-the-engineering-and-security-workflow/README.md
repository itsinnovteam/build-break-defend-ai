# Lab 2 – Trust but verify AI code (CPU only, no GPU)

Full step-by-step instructions are in Module2_Learner_Guide.docx (Part B).

**Two tracks, same lesson:**
- **Track A – Reviewer (no coding):** open `../simulations/sim6_lab2_reviewer_track.html`
  in a browser on your Windows laptop. Nothing to install. You do not need this folder.
- **Track B – Hands-on (Python):** use this folder on your Module 0 VM in OCI.

## Setup (Track B runs on your Module 0 VM in OCI, same as Lab 1)
Nothing to install on your Windows laptop: `ssh` and `scp` are built into Windows 10 and 11.

1. On your Windows laptop, open **Command Prompt** (Windows key, type `cmd`, Enter) and go to the
   folder where you unzipped the package:
```
cd "C:\Users\<you>\Downloads\Module2"
scp -r lab2 <user>@<vm-address>:~/
ssh <user>@<vm-address>
```
   Using an SSH key file? Add `-i "C:\path\to\key"` to both commands (Oracle Linux user in OCI: `opc`).

2. On the VM:
```
cd ~/lab2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama list            # llama3.1:8b must be listed (for Parts 4 and 5)
```
The VM's Python 3.9.25 is fine. If Ollama cannot connect: `sudo systemctl start ollama`.
Edit files with `nano` (`sudo dnf install nano` once) or `vi`.

## Commands you will use
| Command | What it does |
|---|---|
| `python -m pytest -v` | Runs your tests (test_triage_tool.py) |
| `python demo_attacks.py` | Safely shows the bugs the tests do not catch |
| `python meta_test.py` | Tests your TESTS: how many of 7 planted bugs they catch |
| `python -m bandit triage_tool.py` | Security scanner (static analysis) |
| `ollama run llama3.1:8b < prompts/p1_security_review.txt` | AI security review on the VM (Part 4) |
| `ollama run llama3.1:8b < prompts/p2_fix_R6.txt` | Ask the AI to fix one rule (Part 5) |
| `ollama run llama3.1:8b < prompts/p3_tests_R6.txt` | Ask the AI for tests for one rule (Part 5) |
| `python check_fix.py` | Checks your fixed code against SPEC.md (R1–R7) |

Option B (approved chat tool): copy the text of each prompt file into the chat instead.

## Files
| File | Purpose | Edit it? |
|---|---|---|
| triage_tool.py | The AI-generated code you review and fix | YES |
| test_triage_tool.py | The AI-generated tests you strengthen | YES |
| SPEC.md | What the code must do (the contract) | no |
| PROMPTS.md | How to send the prompts, and templates | no |
| prompts/ | Ready-to-send prompt files (P1, P2 per rule, P3 per rule) | no |
| sample_auth.log | Fake SSH log (documentation IPs only) | no |
| demo_attacks.py, meta_test.py, check_fix.py | Lab tools | no |
| meta/, checker/ | Used by the tools – contains answers, don't peek | no |
| solution/ | Instructor answer key – remove before giving to learners if you want | no |

All data is fake. Follow the Module 1 safety rules: never paste real logs or secrets into an AI tool.

## Stretch challenges (experts, Track B)
See the guide, Part B. Challenge 2 adds a new test file `test_r8.py` - keep it separate from
`test_triage_tool.py` so `meta_test.py` keeps working.

## After the lab
Everyone takes `../simulations/final_assessment.html` (pass mark 10 of 12).
