"""
config.py - every Lab 5 setting in one place.

Change a setting here (or with an environment variable) instead of editing the code.
All paths are relative to this lab5 folder, so the lab works from any location.
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- Where the data lives ----------------------------------------------------
SCENARIO_DIR = HERE / "scenarios"          # the synthetic SOC alerts (one JSON each)
STATE_DIR = HERE / "state"                 # created at run time: case notes, blocklist, outbox
AUDIT_FILE = HERE / "agent_audit.log"      # every tool call, who approved it, the result

# ---- Local AI service (Ollama on this VM) ------------------------------------
OLLAMA_URL = os.environ.get("LAB5_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("LAB5_MODEL", "llama3.1:8b")   # must support tool calling
NUM_CTX = 4096
TEMPERATURE = 0

# ---- The agent loop ----------------------------------------------------------
MAX_STEPS = int(os.environ.get("LAB5_MAX_STEPS", "8"))   # hard stop: no runaway loop
MAX_TOOL_CALLS = 10                                      # hard cap on total tool calls

# ---- Risk levels for tools ---------------------------------------------------
# READ   : only reads data, no side effects          -> always allowed
# WRITE  : changes our own systems (notes, blocklist) -> needs approval in v2
# EXTERN : talks to the outside world (email)         -> needs approval; breaks trifecta
READ, WRITE, EXTERN = "read", "write", "extern"

# The DEFENDED agent (v2) may use only these tools for the "triage" job (least privilege).
TRIAGE_ALLOWLIST = ("get_alert", "search_logs", "get_asset_owner", "lookup_ip_reputation",
                    "add_case_note")
# A "response" job may also block an IP - but blocking needs human approval and an argument
# check (see agent.default_validate). Still no disable_account and no send_email.
RESPONSE_ALLOWLIST = TRIAGE_ALLOWLIST + ("block_ip",)

# Human approval is required before any WRITE or EXTERN tool runs (v2)...
REQUIRE_APPROVAL = (WRITE, EXTERN)
# ...except writes to the agent's OWN records, which are part of doing the job.
AUTO_ALLOWED_WRITES = ("add_case_note",)

# Argument allowlists, so a hijacked model cannot aim a real tool at the wrong target.
BLOCKABLE_IP_RANGES = ("198.51.100.", "203.0.113.")   # documentation ranges only (RFC 5737)
EMAIL_ALLOWED_DOMAINS = ("example.com",)              # internal only; never external

NO_RELEVANT = "I could not complete this safely."
