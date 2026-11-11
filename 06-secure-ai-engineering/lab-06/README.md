# Lab 6 - Make the Lab 5 agent deployment-grade (threat model + control document)

Full step-by-step instructions, expected outputs and explanations are in
**Module6_Learner_Guide.docx, chapter 7**. This file is the quick reference.

Lab 6 does not add new agent code. It makes the Lab 5 agent **defendable in front of a CISO**
by producing a **Threat Model & Control Document** - all generated from one machine-readable
model of the system, with every control backed by a real Lab 5 test as evidence.

**Two tracks, same lesson**
- **Track A - walkthrough (no terminal):** open `../simulations/sim6_lab6_walkthrough.html`.
- **Track B - hands-on:** this folder, on your **Module 0 VM** (Oracle Linux 9, Python 3.9). No GPU, no model needed.

## Stack
| Component | Used for | License |
|---|---|---|
| Python 3.9 standard library | all the governance tooling and the document generator | PSF |
| pytest 8.4.2, bandit 1.8.6 | traceability tests and the scan | MIT, Apache 2.0 |

No third-party packages are needed. Nothing calls a model or the network. All data is fictional.

## Phase 1 - Setup
On the VM:
```
cd ~/lab6
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_setup.py
```
`check_setup.py` must end with `All required checks passed.`

## What you run
| Phase | Command | What it does |
|---|---|---|
| 1 Setup | `python check_setup.py` | checks Python, pytest, bandit, and that every artifact is consistent |
| 2 Threat model | `python threat_model.py` | shows where untrusted input enters and the STRIDE threats |
| 3 OWASP | `python owasp.py` | OWASP LLM Top 10 coverage for this system |
| 4 Deployment | `python deployment.py` | recommends a deployment pattern by data sensitivity (local hosting) |
| 5 Compliance | `python compliance.py` | maps controls to NIST AI RMF / ISO 42001 / ISO 27001 / SOC 2 |
| 6 Build the doc | `python build_docs.py` | writes the CISO-ready document to `out/` (Markdown + HTML) |
| 7 Live evidence | `python link_lab5.py` | runs the Lab 5 tests so each control is backed by a passing test |
| 8 Verify | `python -m pytest -v`, `python -m bandit -r . -x ./tests,./.venv` | traceability tests + scan |

**Pass conditions:** `pytest` -> 18 passed · `bandit` -> No issues identified ·
`build_docs.py` -> writes the document · `link_lab5.py` -> Lab 5 tests pass (live evidence).

## The idea in one line
The threat model, the control matrix and the compliance mapping are all **generated from one
model of the system** (`system_model.py`), and **every control is backed by a test**. The
paperwork can never drift from the build, and nothing is claimed that is not proven.

## Files
| File | Purpose |
|---|---|
| `system_model.py` | the system described as data: components, data flows, trust boundaries, data assets |
| `threat_model.py` | STRIDE threats over the boundaries; every threat gets a decision |
| `controls.py` | the control catalogue: mechanism + OWASP + compliance + evidence test |
| `owasp.py` | OWASP LLM Top 10 (2025) and how this system maps to it |
| `deployment.py` | deployment patterns by sensitivity; the local-hosting decision |
| `compliance.py` | controls rolled up to each compliance framework |
| `build_docs.py` | generates the CISO-ready document (Markdown + HTML) |
| `link_lab5.py` | runs the Lab 5 tests to attach live evidence (optional) |
| `check_setup.py` | Phase 1 environment + consistency check |
| `tests/test_lab6.py` | 18 traceability tests - the lab's guarantee |

## Safety
All data is fictional. Lab 6 reads and reasons only; it changes no system and calls no model or
network. Use the generated document as a template for a real review - replace the example
compliance clause ids with your own framework's.
