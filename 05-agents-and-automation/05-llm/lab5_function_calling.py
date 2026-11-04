#!/usr/bin/env python3
"""
Mini-lab - Function calling, step by step (the slide 6 diagram, live; slides 9-13).
AI Bootcamp, Module 5: Agents and Automation.

Every line of output is tagged with the diagram box it belongs to:
  [1 PROMPT]  [2 MESSAGES + TOOL LIST]  [3 LLM]  [4 YOUR CODE]  [5 FUNCTIONS]  [RESULT BACK]

Each tool's arguments are a Pydantic class. The same class does two jobs:
  - box 2: it generates the JSON schema the model reads (a hint)
  - box 4: it validates what the model sends back (a check)
Box 4 then applies a permission guard Pydantic cannot: approved email recipients.

Needs: Python 3.9+, pydantic 2.x (2.13.5 is the newest for Python 3.9),
lab5_agent.py and lab5_data/ from Lab 5. --offline needs no Ollama.

  pip3 install --user "pydantic==2.13.5"
  python3 lab5_function_calling.py --offline           # scripted model replies, same output every time
  python3 lab5_function_calling.py                     # real run with Ollama llama3.1:8b
  python3 lab5_function_calling.py --offline --to soc-archive@northwind-backup.net   # watch the guard
  python3 lab5_function_calling.py --show-schemas      # print every tool schema in step 2
"""
import argparse
import inspect
import json
import sys
import time
import urllib.request
from ipaddress import IPv4Address
from typing import Any, Dict, List, Optional, Tuple

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError
except ImportError:
    sys.exit('Pydantic is not installed. Run:  pip3 install --user "pydantic==2.13.5"')

import lab5_agent as base

ALLOWED_DOMAINS = ["northwind.example"]


# ---------------------------------------------------------------- the argument classes (boxes 2 and 4)
class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")          # unknown argument names are an error


class LookupIpArgs(ToolArgs):
    """Threat-intel reputation for an IPv4 address."""
    ip: IPv4Address = Field(description="IPv4 address only, no port, e.g. 203.0.113.66")


class GetAlertArgs(ToolArgs):
    """Get a SOC alert from the SIEM / EDR by ID."""
    alert_id: str = Field(pattern=r"^NW-\d{4}$", description="Alert ID, e.g. NW-4471")


class GetTenableFindingsArgs(ToolArgs):
    """Tenable vulnerability findings for a host."""
    host: str = Field(pattern=r"^[A-Z]{2,4}-[A-Z]{2}-\d{3}$", description="Hostname, e.g. FIN-LT-022")


class SendEmailArgs(ToolArgs):
    """Send an email. Only approved Northwind recipients are allowed."""
    to: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", description="Recipient address")
    subject: str = Field(min_length=1, max_length=120, description="Subject line")
    body: str = Field(min_length=1, max_length=1500, description="Plain-text body")


# ---------------------------------------------------------------- [5] the functions (from the diagram)
FUNCTIONS = {
    "lookup_ip": (base.lookup_ip, LookupIpArgs),                                  # threat intel
    "get_alert": (base.get_alert, GetAlertArgs),                                  # SIEM / EDR
    "get_tenable_findings": (base.get_tenable_findings, GetTenableFindingsArgs),  # Tenable
    "send_email": (base.send_email, SendEmailArgs),                               # guarded
}


def tool_spec(name: str) -> Dict[str, Any]:
    """Box 2: Pydantic class -> the tool definition the model reads."""
    model = FUNCTIONS[name][1]
    return {"type": "function", "function": {"name": name, "description": inspect.getdoc(model),
                                             "parameters": model.model_json_schema()}}


TOOL_LIST = [tool_spec(n) for n in FUNCTIONS]


def tag(box: str, text: str = "") -> None:
    print("[%s] %s" % (box, text))


def show(obj: Any, limit: int = 400, indent: str = "      ") -> None:
    s = obj if isinstance(obj, str) else json.dumps(obj, default=str)
    if len(s) > limit:
        s = s[:limit] + " ...(%d chars)" % len(s)
    print(indent + s)


# ---------------------------------------------------------------- [3] the LLM
def call_llm(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    body = json.dumps({"model": base.MODEL, "messages": messages, "tools": TOOL_LIST,
                       "stream": False, "options": {"temperature": 0.3}}).encode()
    req = urllib.request.Request(base.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def scripted_llm(to: str):
    """--offline: replays what llama3.1:8b typically does, so the lab works without Ollama.
    Step 2 copies '203.0.113.66:443' from the alert text - a classic model mistake."""
    def call(name, **args):
        return {"message": {"role": "assistant", "content": "",
                            "tool_calls": [{"function": {"name": name, "arguments": args}}]}, "eval_count": 28}
    replies = iter([
        call("get_alert", alert_id="NW-4471"),
        call("lookup_ip", ip="203.0.113.66:443"),
        call("lookup_ip", ip="203.0.113.66"),
        call("get_tenable_findings", host="FIN-LT-022"),
        call("send_email", to=to, subject="NW-4471 triage: HIGH",
             body="FIN-LT-022 beacons to known C2 203.0.113.66 every 60 s; critical VPN client RCE unpatched. "
                  "Recommend isolate, block IP, patch."),
        None,                                            # final answer, built from what happened
    ])

    def reply(messages):
        r = next(replies)
        if r is not None:
            return r
        sent = "refused" not in messages[-1]["content"]
        return {"message": {"role": "assistant", "content":
            "Severity: HIGH. FIN-LT-022 (j.reyes) runs vpnhelper.exe beaconing to 203.0.113.66, a known "
            "Cobalt Strike C2. The host has a critical, 41-day-old VPN client RCE. Actions: isolate FIN-LT-022 "
            "(call the Finance duty manager first), block 203.0.113.66, patch the VPN client. "
            + ("Summary emailed to the SOC lead." if sent else
               "I could not email the summary: the recipient was refused.")}, "eval_count": 85}
    return reply


# ---------------------------------------------------------------- [4] your code: validate, guard, route
def validate(name: str, args: Any) -> Tuple[Optional[BaseModel], Optional[Dict[str, Any]]]:
    """Shape check with Pydantic. Returns (validated object, None) or (None, error to send back)."""
    if name not in FUNCTIONS:
        return None, {"error": "unknown function %r" % name}
    model = FUNCTIONS[name][1]
    try:
        if isinstance(args, str):                         # some models send arguments as a JSON string
            return model.model_validate_json(args or "{}"), None
        return model.model_validate(args or {}), None
    except ValidationError as e:
        return None, {"error": "invalid arguments",
                      "details": [{"field": ".".join(map(str, err["loc"])) or "(arguments)",
                                   "problem": err["msg"], "got": err.get("input")}
                                  for err in e.errors(include_url=False)]}


def guard(name: str, clean: Dict[str, Any]) -> Optional[str]:
    """Permission check: Pydantic can't know who is an approved recipient. Your code does."""
    if name == "send_email":
        domain = clean["to"].rsplit("@", 1)[-1].lower()
        if domain not in ALLOWED_DOMAINS:
            return "%s is not an approved recipient domain" % domain
    return None


def short(args: Any) -> str:
    vals = args.values() if isinstance(args, dict) else [args]
    return ", ".join(str(v) for v in vals)


# ---------------------------------------------------------------- the run
def main() -> None:
    ap = argparse.ArgumentParser(description="Function calling, step by step (with Pydantic)")
    ap.add_argument("--offline", action="store_true", help="scripted model replies (no Ollama)")
    ap.add_argument("--to", default="soc-lead@northwind.example", help="who the summary is emailed to")
    ap.add_argument("--show-schemas", action="store_true", help="print every tool schema in step 2")
    ap.add_argument("--steps", type=int, default=8, help="step budget")
    a = ap.parse_args()
    llm = scripted_llm(a.to) if a.offline else call_llm
    trace = []  # type: List[List[str]]

    # [1] PROMPT
    messages = [
        {"role": "system", "content": "You are Nova, the Northwind SOC night-shift assistant. Use the tools to "
                                      "investigate. Then email a short summary and give your triage: severity, "
                                      "evidence, actions."},
        {"role": "user", "content": "Triage NW-4471 and email a two-line summary to %s." % a.to},
    ]
    print("=" * 78)
    tag("1 PROMPT", "what the analyst asked")
    show(messages[1]["content"])
    tag("1 PROMPT", "plus the system prompt (Nova's role and rules)")
    show(messages[0]["content"], 160)

    # [2] MESSAGES + TOOL LIST
    tag("2 MESSAGES + TOOL LIST", "sent to %s with model %s%s"
        % (base.OLLAMA_URL, base.MODEL, " (offline: scripted replies)" if a.offline else ""))
    tag("2 MESSAGES + TOOL LIST", "tools offered: " + ", ".join(FUNCTIONS))
    tag("2 MESSAGES + TOOL LIST", "schemas generated from the Pydantic classes with model_json_schema():")
    for t in (TOOL_LIST if a.show_schemas else TOOL_LIST[:1]):
        show(t, 700)
    if not a.show_schemas:
        print("      (one schema shown; --show-schemas prints all 4. They are sent on EVERY request.)")

    for step in range(1, a.steps + 1):
        print("-" * 78)
        t0 = time.time()
        raw = llm(messages)
        msg = raw.get("message", {})
        calls = base.extract_calls(msg)

        # [3] LLM
        tag("3 LLM", "step %d, %.1f s, %s output tokens" % (step, time.time() - t0, raw.get("eval_count", "?")))
        if not calls:
            tag("3 LLM", "no tool call -> it answered. Loop ends.")
            print("=" * 78)
            tag("FINAL ANSWER")
            show(msg.get("content", "").strip(), 2000)
            trace.append([str(step), "(answer)", "-", "-"])
            break
        tag("3 LLM", "asked for a tool (it does not run anything):")
        show({"tool_calls": msg.get("tool_calls") or "(written as text, parsed by extract_calls)"})
        messages.append({"role": "assistant", "content": msg.get("content", ""),
                         "tool_calls": msg.get("tool_calls") or []})

        for c in calls:
            name, args = c["name"], c["arguments"]
            # [4] YOUR CODE: 1) Pydantic shape check  2) permission guard  3) route
            obj, error = validate(name, args)
            if error:
                tag("4 YOUR CODE", "Pydantic: REJECTED - the function does not run. Error sent back:")
                show(error)
                result = error
                trace.append([str(step), "%s(%s)" % (name, short(args)), "rejected",
                              error.get("details", [{}])[0].get("problem", error["error"])])
            else:
                model_name = FUNCTIONS[name][1].__name__
                clean = obj.model_dump(mode="json")
                tag("4 YOUR CODE", "Pydantic: OK -> %r" % obj)
                reason = guard(name, clean)
                if reason:
                    tag("4 YOUR CODE", "guard: REFUSED - " + reason)
                    result = {"refused": reason}
                    trace.append([str(step), "%s(%s)" % (name, short(args)), "refused", reason])
                else:
                    tag("4 YOUR CODE", "guard: allowed -> route to %s()" % name)
                    # [5] FUNCTIONS
                    result = FUNCTIONS[name][0](**clean)
                    tag("5 FUNCTIONS", "%s(%s) returned:"
                        % (name, ", ".join("%s=%s" % (k, json.dumps(v)) for k, v in clean.items())))
                    show(result)
                    trace.append([str(step), "%s(%s)" % (name, short(clean)), "ran",
                                  json.dumps(result, default=str)[:60]])
            base.audit({"lab": "fc", "tool": name, "args": args,
                        "refused": None if "refused" not in result and "error" not in result else str(result)[:120],
                        "hijack": False})
            # [RESULT BACK]
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})
            tag("RESULT BACK", "added as a tool message -> %d messages; the LLM reads it next step"
                % len(messages))
    else:
        tag("4 YOUR CODE", "step budget of %d reached, stopping" % a.steps)

    print("=" * 78)
    tag("TRACE", "one row per trip around the diagram")
    print("      %-4s %-46s %-9s %s" % ("step", "LLM asked for", "box 4", "result"))
    for row in trace:
        print("      %-4s %-46s %-9s %s" % (row[0], row[1][:46], row[2], row[3][:44]))


if __name__ == "__main__":
    main()
