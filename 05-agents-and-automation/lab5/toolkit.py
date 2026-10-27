"""
toolkit.py - the SOC agent's tools, each with a schema, a risk level, and a real action.

A "tool" (also called a function) is a normal Python function the model can ask us to run.
We describe it to the model in JSON; the MODEL only ever RETURNS a request to call a tool.
OUR CODE decides whether to run it (agent.py). That boundary is the whole security story.

Risk levels (config.py):
  READ   - only reads data, no side effects        (get_alert, search_logs, ...)
  WRITE  - changes our own systems                 (add_case_note, block_ip, disable_account)
  EXTERN - talks to the outside world              (send_email)  <- breaks the "lethal trifecta"

All data is fake. Tools act on local files under state/, never on real systems or the network.
"""

import datetime
import ipaddress
import json
import re
from pathlib import Path

import config

_ALERTS = None


def _load_alerts():
    global _ALERTS
    if _ALERTS is None:
        _ALERTS = {}
        for path in sorted(config.SCENARIO_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            _ALERTS[data["alert_id"]] = data
    return _ALERTS


def _state_file(name):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        config.STATE_DIR.chmod(0o700)
    except OSError:
        pass
    return config.STATE_DIR / name


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ToolError(Exception):
    """A tool refused to run (bad arguments, blocked target). Fail safe, not loud."""


# ---------- READ tools --------------------------------------------------------
def get_alert(alert_id: str):
    """Return the full SOC alert, including any analyst comments on the ticket."""
    alert = _load_alerts().get(str(alert_id).strip())
    if not alert:
        raise ToolError(f"no alert named {alert_id!r}")
    return alert


def search_logs(user: str = "", ip: str = "", hours: int = 24):
    """Search authentication logs (fake) by user and/or source IP for the last N hours."""
    rows = _load_alerts()
    hits = []
    for alert in rows.values():
        for row in alert.get("auth_log", []):
            if (not user or row["user"] == user) and (not ip or row["ip"] == ip):
                hits.append(row)
    return {"query": {"user": user, "ip": ip, "hours": hours}, "count": len(hits), "events": hits[:20]}


def get_asset_owner(asset: str):
    """Look up who owns a host or account in the CMDB (fake)."""
    cmdb = {
        "web-prod-03": {"owner": "DevOps", "critical": True},
        "db-fin-02": {"owner": "IT Operations", "critical": True},
        "svc-backup": {"owner": "IT Operations", "critical": True, "note": "service account, do not disable"},
        "m.reyes": {"owner": "Finance", "critical": False},
        "build-agent-03": {"owner": "DevOps", "critical": False},
    }
    info = cmdb.get(str(asset).strip())
    if not info:
        raise ToolError(f"no asset named {asset!r} in the CMDB")
    return dict(info, asset=asset)


def lookup_ip_reputation(ip: str):
    """Check an IP address against a threat-intel feed (fake, deterministic)."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ToolError(f"{ip!r} is not a valid IP address")
    bad = {"198.51.100.20": 92, "203.0.113.10": 77}
    score = bad.get(ip, 5)
    return {"ip": ip, "risk_score": score, "verdict": "malicious" if score >= 70 else "clean"}


# ---------- WRITE tools (need approval in v2) ---------------------------------
def add_case_note(alert_id: str, note: str):
    """Append a note to the local case file for an alert. Changes our own records only."""
    path = _state_file("case_notes.log")
    line = {"time": _now(), "alert_id": str(alert_id), "note": str(note)[:500]}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    return {"written": True, "alert_id": alert_id}


def block_ip(ip: str):
    """Add an IP address to the firewall blocklist (fake, local file)."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ToolError(f"{ip!r} is not a valid IP address")
    path = _state_file("blocklist.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(ip + "\n")
    return {"blocked": ip}


def disable_account(account: str):
    """Disable a user or service account (fake). High impact: can break production."""
    path = _state_file("disabled_accounts.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(str(account) + "\n")
    return {"disabled": account}


# ---------- EXTERN tool (needs approval; breaks the trifecta) -----------------
def send_email(to: str, subject: str, body: str):
    """Send an email to the OUTSIDE world (fake outbox). This is how data leaves the building."""
    path = _state_file("outbox.log")
    line = {"time": _now(), "to": to, "subject": str(subject)[:120], "body": str(body)[:500]}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    return {"sent": True, "to": to}


# ---------- the registry: name -> (function, risk, schema) --------------------
def _schema(name, description, properties, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


_S = {"type": "string"}
_I = {"type": "integer"}

REGISTRY = {
    "get_alert": (get_alert, config.READ, _schema(
        "get_alert", "Get a SOC alert and its ticket comments by alert id, e.g. A-1007.",
        {"alert_id": _S}, ["alert_id"])),
    "search_logs": (search_logs, config.READ, _schema(
        "search_logs", "Search authentication logs by user and/or source IP.",
        {"user": _S, "ip": _S, "hours": _I}, [])),
    "get_asset_owner": (get_asset_owner, config.READ, _schema(
        "get_asset_owner", "Look up who owns a host or account in the CMDB.",
        {"asset": _S}, ["asset"])),
    "lookup_ip_reputation": (lookup_ip_reputation, config.READ, _schema(
        "lookup_ip_reputation", "Check an IP address against threat intel.",
        {"ip": _S}, ["ip"])),
    "add_case_note": (add_case_note, config.WRITE, _schema(
        "add_case_note", "Append a note to the case file for an alert.",
        {"alert_id": _S, "note": _S}, ["alert_id", "note"])),
    "block_ip": (block_ip, config.WRITE, _schema(
        "block_ip", "Add an IP address to the firewall blocklist.",
        {"ip": _S}, ["ip"])),
    "disable_account": (disable_account, config.WRITE, _schema(
        "disable_account", "Disable a user or service account. High impact.",
        {"account": _S}, ["account"])),
    "send_email": (send_email, config.EXTERN, _schema(
        "send_email", "Send an email. Can reach outside the company.",
        {"to": _S, "subject": _S, "body": _S}, ["to", "subject", "body"])),
}


def tool_names():
    return tuple(REGISTRY)


def risk_of(name):
    return REGISTRY[name][1] if name in REGISTRY else None


def schemas_for(names):
    """The JSON tool list to send to the model, for the given tool names (in order)."""
    return [REGISTRY[n][2] for n in names if n in REGISTRY]


def run_tool(name, arguments):
    """Run one tool by name with a dict of arguments. Raises ToolError or KeyError on misuse."""
    if name not in REGISTRY:
        raise ToolError(f"unknown tool {name!r}")
    func = REGISTRY[name][0]
    if not isinstance(arguments, dict):
        raise ToolError("tool arguments must be an object")
    return func(**arguments)
