# Lab 5 – Build an agent, then hijack it

AI Bootcamp, Module 5: Agents and Automation. All data is fictional.

## Requirements
Module 0 VM: Oracle Linux, Python 3.9+, Ollama running `llama3.1:8b` (CPU is fine). The mini-lab and Lab 5B use Pydantic: `pip3 install --user "pydantic==2.13.5"` (the newest release that supports Python 3.9).

## Files
- `lab5_agent.py` – the agent loop, tools, the `Gate` (step 3), audit log
- `lab5_function_calling.py` – Mini-lab (slides 9–13): the slide 6 function-calling diagram, run live with Pydantic argument classes; every output line is tagged with its box (`--offline` needs no Ollama)
- `lab5_data/soc.json` – Northwind SOC alerts, intel, Tenable findings, case notes, reported phishing email PH-0192
- `lab5_data/life.json` – Ana's calendar, weather and inbox (includes the fake parcel email)
- Created at runtime: `lab5_data/outbox.log` (anything "sent" or changed), `lab5_data/audit.jsonl` (every tool call)

Companion lab: `LAB5B.md` + `lab5b_pydantic.py` (needs `pip3 install --user "pydantic==2.13.5"`).

## Mini-lab – Function calling, step by step (before Part A)
    pip3 install --user "pydantic==2.13.5"
    python3 lab5_function_calling.py --offline
    python3 lab5_function_calling.py
    python3 lab5_function_calling.py --offline --to soc-archive@northwind-backup.net

