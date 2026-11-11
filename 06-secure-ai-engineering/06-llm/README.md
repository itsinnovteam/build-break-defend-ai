## Lab 6 – Make Nova deployment grade

Module 6: Secure AI Engineering. About 90 minutes.

You write a **threat model and control document** for Nova that you could defend in front of the CISO,
for one decision: *may Nova triage reported phishing in production?*
The VM produces the evidence; you write the document on your laptop.

## What's in this folder

| File | What it does |
|---|---|
| `lab6_collect.sh` | Re-runs the Lab 5 attack once per defence and collects all evidence into `~/lab6/evidence` |
| `lab6_redact.py` | Redacts secrets from tool results (rule 2: redact at the tool boundary) and writes the redaction evidence |
| `lab6_index.py` | Checks every evidence file and writes `evidence_index.md` (your section 6) |
| `lab6_template.docx` | The document you fill in: 7 sections with table shells |
| `lab6_example.docx` | Instructor answer key (not for learners until after the lab) |

Standard library only: no `pip install`. Needs the Lab 5 files in `../05-llm`.

## Setup

Copy this folder next to `05-llm`, so you have:

```
~/security-for-ai-boothcamp/
  05-llm/       lab5_hijack.py, lab5_hijack_data/
  06-secure/    this folder
```

```bash
cd ~/security-for-ai-boothcamp/06-secure
python3 lab6_redact.py --selftest      # expect: selftest: PASS
mkdir -p ~/lab6/evidence
```

## Step 1 – Scope, draw, classify (20 min) → sections 1–3

Open `lab6_template.docx`. Write the scope and the **"Nova must never"** list.
Redraw slide 6's diagram, mark both trust boundaries and every untrusted entry point.
Classify each asset (Restricted / Confidential / Internal / Public).

## Step 2 – Threats and risk register (25 min) → section 4

Walk each boundary crossing with STRIDE; name each threat with OWASP 2026 IDs (LLM01–10, ASI01–10).
Score Likelihood 1–3 × Impact 1–3 using **your own Lab 5 numbers**. At least one threat per STRIDE letter.

## Step 3 – Controls and evidence (30 min) → sections 5–6

```bash
cd ~/security-for-ai-boothcamp/06-secure
bash lab6_collect.sh             # baselines, lp, taint, allow, platform, redaction
bash lab6_collect.sh --approve   # optional: also the approve guard – answer N to every prompt
```

What you should see:

| Evidence | Expected |
|---|---|
| `baseline-none`, `baseline-prompt` | **HIJACKED** – proves the threat is real |
| `guard-lp`, `guard-taint`, `guard-allow`, `guard-approve` | **ATTEMPTED (blocked)**, outbox empty |
| `ports.txt` | Ollama on `127.0.0.1:11434` only |
| `model.txt` | `llama3.1:8b` and its ID |
| `case-notes-redacted.txt` | `[REDACTED:TOKEN]`, no `nw_…` token |

The script ends by printing PASS/FAIL per file and writing `~/lab6/evidence/evidence_index.md`.
Paste that table into section 6. Every control in section 5 must cite one evidence file.

Re-check at any time with `python3 lab6_index.py`.

## Step 4 – Residual risk and go-live (15 min) → section 7

State what the guards **don't** stop (INFLUENCED: the model's words), who accepts it and until when,
the go-live conditions, the kill switch and the review trigger.

## Defend it

In pairs: one presents, one plays the CISO and asks three of the seven questions on slide 37.
Every answer must point to a section – and, where it applies, an evidence file.

## Using the redactor in your own agent

Wrap the tool, not the prompt:

```python
from lab6_redact import redact_text

def get_case_notes(case_id):
    return redact_text(base.get_case_notes(case_id))
```

## Troubleshooting

- `lab5_hijack.py not found` – run from `06-secure`, or set `LAB5_DIR=/path/to/05-llm`.
- `no listener on port 11434` – start Ollama, then re-run `bash lab6_collect.sh`.
- A guard run shows **HIJACKED** – that control failed. Record it in section 7; don't hide it.
- Want evidence elsewhere – `EVIDENCE_DIR=/path bash lab6_collect.sh`.
