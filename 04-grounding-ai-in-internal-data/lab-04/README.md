# Lab 4 - Build, break and secure a RAG assistant (CPU only, open source)

Full step-by-step instructions, expected outputs and explanations are in
**Module4_Learner_Guide.docx, chapter 7**. This file is the quick reference.

**Two tracks, same lesson**
- **Track A - walkthrough (no terminal):** open `../simulations/sim5_lab4_walkthrough.html` in a browser.
- **Track B - hands-on:** this folder, on your **Module 0 VM** (Oracle Linux 9, Python 3.9, Ollama). No GPU.

## Stack
| Component | Used for | License |
|---|---|---|
| Ollama + `llama3.1:8b` | chat model (answers) | MIT / Llama 3.1 Community License (open weights) |
| Ollama + `all-minilm` | embedding model, 384 numbers per text | Apache 2.0 |
| SQLite (built into Python) | vector store `index/vectors.db` | public domain |
| Python 3.9 standard library | all lab code | PSF |
| pytest 8.4.2, bandit 1.8.6 | tests and scan (Phase 6 only) | MIT, Apache 2.0 |

Why not ChromaDB here? ChromaDB 1.5.9 refuses to import with SQLite older than 3.35, and Oracle Linux 9
ships 3.34.1. `vectorstore.py` does the same three jobs (store, filter in the query, cosine search) with
no extra packages. In production use a real vector database (Chroma, pgvector, Qdrant, ...) with the same
pattern: the role filter goes inside the query.

## Phase 1 - Setup
Windows laptop, **Command Prompt** (nothing to install; no PowerShell):
```
cd "%USERPROFILE%\Downloads\Module4"
scp -r lab4 <user>@<vm-address>:~/
ssh -o ServerAliveInterval=30 <user>@<vm-address>
```
On the VM:
```
ollama pull all-minilm
cd ~/lab4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_setup.py
```
`check_setup.py` must end with `All required checks passed.` After every new login:
`cd ~/lab4` and `source .venv/bin/activate`.

## What you run (no code editing)
| Phase | Commands | Chat model? |
|---|---|---|
| 2 Documents | `ls kb`, `cat kb/HR-001_emergency_leave_policy.md`, `cat config/directory.json` | no |
| 3 Build | `python ingest.py`, `python embed_demo.py`, `python why_rag.py`, `python ask.py --user ana "Who approves a Tenable risk exception?" --dry-run` (then without `--dry-run`), `python ask.py --user carl "When does the CAB meet?"` (then add `--mode hybrid`), `python ask.py --user ben "ClamAV flagged a file on build-agent-03. What do we do now?"`, `python experiments.py` | some |
| 4 Break (v1) | `python ask_v1.py --user dana "What are the salary bands for senior engineers?" --dry-run`, the same without `--dry-run`, with `--role hr`, `--user eve` | 1 to 3 |
| 5 Secure (v2) | `grep -n "THE FIX" -A3 assistant.py`, the same attacks with `python ask.py ...`, `--model-location cloud`, `tail -n 3 rag_audit.log` | 2 |
| 6 Verify | `python attacks.py`, `python -m pytest -v`, `python -m bandit -r . -x ./tests,./.venv` | no |
| 7 Reflect | questions and challenges in the guide, then `../simulations/final_assessment.html` | no |

Each chat answer takes about 30 to 120 seconds on a CPU. Use `--dry-run` to see retrieval and the exact
prompt without calling the chat model.

**Pass conditions:** `attacks.py` -> v2 blocked 9 of 9, answered 6 of 6 · `pytest` -> 62 passed ·
`bandit` -> No issues identified.

## Users (config/directory.json - the trusted directory)
| User | Roles | Who |
|---|---|---|
| ana | employee, soc | SOC analyst (Tenable) |
| ben | employee, devops | DevOps engineer |
| carl | employee, itops | IT Operations |
| hana | employee, hr | HR officer |
| sam | employee, soc, security-lead | Security lead |
| dana | contractor | External contractor |
| eve | - | not in the directory (tests "access denied") |

`--user` stands in for the SSO login. Roles come only from the directory - never from the question or an option.

## What the secure assistant (v2) enforces in code
1. Roles from the trusted directory; unknown user, no roles or a broken directory -> denied (exit code 2).
2. Access control at retrieval: the role filter is inside the vector-store SQL query, down to the chunk.
3. Data residency: `local-only` chunks never reach a cloud model (simulated) or a remote embedding service.
4. Documents with instructions aimed at the AI are held back as a whole; the owner is named.
5. No disclosure by existence: same answer as for a topic that does not exist.
6. Fresh index only: if `kb/` changed after `ingest.py`, refuse and say so.
7. Audit log `rag_audit.log` (permissions 600): who, roles, chunks, blocked counts, outcome - no question or answer text.

## Exit codes
`0` answered or "I could not find this" · `1` setup problem (no index, Ollama down, stale index) · `2` access denied or a forbidden option.

## Reset
```
cd ~/lab4
rm -f kb/SEC-005_soc_shift_handover.md
unset LAB4_EMBED_MODEL
rm -rf index rag_audit.log
python ingest.py
```

## Safety
All data is fake. Run the attacks only against this lab on your own VM. At work, follow the Module 1
rules: never put real secrets or personal data into AI tools that are not approved.
