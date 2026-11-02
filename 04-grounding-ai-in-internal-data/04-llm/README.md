# Module 4 Lab Pack - Grounding AI in Internal Data (RAG)

Runs on the Module 0 lab VM: Oracle Linux 9, Python 3.9, Ollama, CPU only.
No pip installs: the scripts use the Python standard library.

## One-time setup

    ollama pull nomic-embed-text
    ollama list                       # should show llama3.1:8b and nomic-embed-text
    cd ~/module4_rag_lab

## Files

| File | Lab | Pipeline stage |
| --- | --- | --- |
| baseline.py | 4.1 | Ask with no internal data |
| chunker.py | 4.2 | Load + chunk |
| indexer.py | 4.3 | Embed + store (index.json) |
| retriever.py | 4.4, 4.7 | Retrieve (+ role filter TODO) |
| ask.py | 4.5, 4.6 | Augment + generate + citation check |
| docs/ | all | Fictional Northwind playbooks (the "internal data") |
| lab46_extra_docs/ | 4.6 | A stale playbook and a poisoned vendor advisory |
| solutions/ | 4.7 | Solution for the role filter |

## Quick run

    python3 baseline.py
    python3 chunker.py
    python3 indexer.py
    python3 retriever.py "who do I escalate a compromised admin account to?"
    python3 ask.py "How should I investigate multiple failed logins followed by a successful login from an unusual location?"

All documents are fictional training material for the AI Bootcamp.
