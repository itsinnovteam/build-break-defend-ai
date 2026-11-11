# Lab 5 – Build an agent, then hijack it

AI Bootcamp, Module 5: Agents and Automation. All data is fictional.

## Requirements
Module 0 VM: Oracle Linux, Python 3.9+, Ollama running `llama3.1:8b` (CPU is fine). Lab 5 Parts A–D are standard library only. The mini-lab and Lab 5B use Pydantic: `pip install "pydantic==2.13.5"` inside a venv, or `pip3 install --user "pydantic==2.13.5"` without one (2.13.5 is the newest release that supports Python 3.9).

## Files
- `lab5_agent.py` – the agent loop, tools, the `Gate` (step 3), audit log
- `lab5_function_calling.py` – Mini-lab: ONE function call (the function-calling diagram, live) with Pydantic argument classes; request 1 may call one tool, request 2 offers no tools so the model must answer. Every line is tagged with its box (`--offline` needs no Ollama)
- `lab5_agent_loop.py` – Loop lab: continues the mini-lab; the agent-loop diagram run live, every line tagged [1 GOAL IN] … [6 STOP] (`--offline`, `--alert NW-4475`, `--max-steps 3`, `--workflow`)
- `lab5b_pydantic.py` + `LAB5B.md` – Lab 5B: the same agent with Pydantic argument models, every stage printed
- `lab5_data/soc.json` – Northwind SOC alerts, intel, Tenable findings, case notes, reported phishing email PH-0192
- `lab5_data/life.json` – Ana's calendar, weather and inbox (includes the fake parcel email)
- Created at runtime: `lab5_data/outbox.log` (anything "sent" or changed), `lab5_data/audit.jsonl` (every tool call)

Companion lab: `LAB5B.md` + `lab5b_pydantic.py` (needs `pip3 install --user "pydantic==2.13.5"`).

## Mini-lab – Function calling, step by step (before Part A)
    pip3 install --user "pydantic==2.13.5"
    python3 lab5_function_calling.py --offline
    python3 lab5_function_calling.py
    python3 lab5_function_calling.py --offline --bad-args
    python3 lab5_function_calling.py --offline --task email --to soc-archive@northwind-backup.net

## Loop lab – The agent loop (after the mini-lab)
    python lab5_agent_loop.py --offline
    python lab5_agent_loop.py --offline --alert NW-4475
    python lab5_agent_loop.py --offline --max-steps 3
    python lab5_agent_loop.py --offline --alert NW-4475 --workflow
    python lab5_agent_loop.py


