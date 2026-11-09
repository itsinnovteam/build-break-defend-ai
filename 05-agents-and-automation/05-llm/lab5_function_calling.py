#!/usr/bin/env python3
"""
Mini-lab - ONE function call, step by step (the slide 4 diagram, live).
AI Bootcamp, Module 5: Agents and Automation.

Exactly one trip around the diagram, then the model must answer:
  request 1: the model may call ONE tool  -> your code checks and runs it -> result back
  request 2: your code offers NO tools    -> the model can only answer
There is no loop here. lab5_agent_loop.py lets it keep going.

Every line of output is tagged with the diagram box it belongs to:
  [1 PROMPT]  [2 MESSAGES + TOOL LIST]  [3 LLM]  [4 YOUR CODE]  [5 FUNCTIONS]  [RESULT BACK]

Needs: Python 3.9+, pydantic 2.x (2.13.5 is the newest for Python 3.9),
lab5_agent.py and lab5_data/ from Lab 5. --offline needs no Ollama.

  pip install "pydantic==2.13.5"            (inside a venv; without one: pip3 install --user ...)
  python3 lab5_function_calling.py --offline                     # one call: lookup_ip
  python3 lab5_function_calling.py --offline --bad-args          # the model adds the port: validate() rejects it
  python3 lab5_function_calling.py --offline --task email --to soc-archive@northwind-backup.net   # guard() rejects it
  python3 lab5_function_calling.py                               # real run with Ollama llama3.1:8b
  python3 lab5_function_calling.py --show-schemas                # print every tool schema in step 2
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
    sys.exit('Pydantic is not installed. Run:  pip install "pydantic==2.13.5"')

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

TASKS = {
    "ip": "Alert NW-4471: process vpnhelper.exe on FIN-LT-022 connects to 203.0.113.66:443 every 60 s. "
          "Is the destination IP malicious?",
    "email": "Email a two-line summary of alert NW-4471 to {to}: FIN-LT-022 beacons to 203.0.113.66, "
             "a known C2 server. Severity HIGH.",
}


def tag(box: str, text: str = "") -> None:
    print("[%s] %s" % (box, text))


def show(obj: Any, limit: int = 400, indent: str = "      ") -> None:
    s = obj if isinstance(obj, str) else json.dumps(obj, default=str)
    if len(s) > limit:
        s = s[:limit] + " ...(%d chars)" % len(s)
    print(indent + s)


# ---------------------------------------------------------------- [3] the LLM
def call_llm(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    body = {"model": base.MODEL, "messages": messages, "stream": False, "options": {"temperature": 0.3}}
    body["tools"] = TOOL_LIST if tools is None else tools
    req = urllib.request.Request(base.OLLAMA_URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def scripted_llm(task: str, to: str, bad_args: bool):
    """--offline: replays what llama3.1:8b typically does, so the lab works without Ollama."""
    def call(name, **args):
        return {"message": {"role": "assistant", "content": "",
                            "tool_calls": [{"function": {"name": name, "arguments": args}}]}, "eval_count": 24}

    def answer(text):
        return {"message": {"role": "assistant", "content": text}, "eval_count": 60}

    def reply(messages, tools=None):
        if messages[-1]["role"] != "tool":                       # request 1: the model picks a tool
            if task == "email":
                return call("send_email", to=to, subject="NW-4471 triage: HIGH",
                            body="FIN-LT-022 beacons to 203.0.113.66, a known C2 server. Severity HIGH.")
            return call("lookup_ip", ip="203.0.113.66:443" if bad_args else "203.0.113.66")
        result = messages[-1]["content"]                           # request 2: no tools, so it answers
        if "error" in result:
            return answer("I couldn't check the reputation: the IP I sent included the port (:443) and was "
                          "rejected. Re-run the lookup with 203.0.113.66.")
        if "refused" in result:
            return answer("I could not send the summary: the recipient was refused.")
        if task == "email":
            return answer("Done: the NW-4471 summary was emailed to %s." % to)
        return answer("Yes. 203.0.113.66 is malicious: threat intel tags it as a Cobalt Strike C2 server, "
                      "first seen 2026-10-28. FIN-LT-022 is likely compromised; escalate NW-4471.")
    return reply


# ---------------------------------------------------------------- [4] your code: validate, guard, route
def validate(name: str, args: Any) -> Tuple[Optional[BaseModel], Optional[Dict[str, Any]]]:
    """Your code's shape check, using Pydantic. Returns (validated object, None) or (None, error to send back)."""
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
    """Your code's permission check: Pydantic can't know who is an approved recipient."""
    if name == "send_email":
        domain = clean["to"].rsplit("@", 1)[-1].lower()
        if domain not in ALLOWED_DOMAINS:
            return "%s is not an approved recipient domain" % domain
    return None


def run_call(name: str, args: Any) -> Tuple[Any, str]:
    """Box 4 then box 5 for one call. Returns (result to send back, what happened)."""
    obj, error = validate(name, args)
    if error:
        tag("4 YOUR CODE", "validate(): REJECTED by your code (Pydantic check failed). The function does not run.")
        show(error)
        return error, "REJECTED by your code · validate()"
    clean = obj.model_dump(mode="json")
    tag("4 YOUR CODE", "validate(): OK (Pydantic) -> %r" % obj)
    reason = guard(name, clean)
    if reason:
        tag("4 YOUR CODE", "guard(): REJECTED by your code - " + reason)
        return {"refused": reason}, "REJECTED by your code · guard()"
    tag("4 YOUR CODE", "guard(): allowed -> route to %s()" % name)
    result = FUNCTIONS[name][0](**clean)
    tag("5 FUNCTIONS", "%s(%s) returned:" % (name, ", ".join("%s=%s" % (k, json.dumps(v)) for k, v in clean.items())))
    show(result)
    return result, "ran %s()" % name


# ---------------------------------------------------------------- the run: one trip, then answer
def main() -> None:
    ap = argparse.ArgumentParser(description="One function call, step by step (with Pydantic)")
    ap.add_argument("--offline", action="store_true", help="scripted model replies (no Ollama)")
    ap.add_argument("--task", choices=list(TASKS), default="ip", help="ip = check the IP, email = send a summary")
    ap.add_argument("--to", default="soc-lead@northwind.example", help="recipient for --task email")
    ap.add_argument("--bad-args", action="store_true", help="--offline only: the model includes the port")
    ap.add_argument("--show-schemas", action="store_true", help="print every tool schema in step 2")
    a = ap.parse_args()
    llm = scripted_llm(a.task, a.to, a.bad_args) if a.offline else call_llm

    # [1] PROMPT
    messages = [
        {"role": "system", "content": "You are Nova, the Northwind SOC night-shift assistant. Use a tool if you "
                                      "need one, then answer briefly."},
        {"role": "user", "content": TASKS[a.task].format(to=a.to)},
    ]
    print("=" * 78)
    tag("1 PROMPT", "what the analyst asked")
    show(messages[1]["content"])
    tag("1 PROMPT", "plus the system prompt (Nova's role and rules)")
    show(messages[0]["content"])

    # [2] MESSAGES + TOOL LIST
    tag("2 MESSAGES + TOOL LIST", "request 1 to %s with model %s%s"
        % (base.OLLAMA_URL, base.MODEL, " (offline: scripted replies)" if a.offline else ""))
    tag("2 MESSAGES + TOOL LIST", "tools offered: " + ", ".join(FUNCTIONS))
    tag("2 MESSAGES + TOOL LIST", "schemas generated from the Pydantic classes with model_json_schema():")
    for t in (TOOL_LIST if a.show_schemas else TOOL_LIST[:1]):
        show(t, 700)
    if not a.show_schemas:
        print("      (one schema shown; --show-schemas prints all 4)")

    # [3] LLM, request 1: it may ask for a tool
    print("-" * 78)
    t0 = time.time()
    raw = llm(messages)
    msg = raw.get("message", {})
    calls = base.extract_calls(msg)
    tag("3 LLM", "request 1, %.1f s, %s output tokens" % (time.time() - t0, raw.get("eval_count", "?")))
    if not calls:
        tag("3 LLM", "no tool call: it answered straight away. Nothing for your code to run.")
        print("=" * 78)
        tag("FINAL ANSWER")
        show((msg.get("content") or "").strip(), 2000)
        return
    tag("3 LLM", "asked for a tool (it does not run anything):")
    show({"tool_calls": msg.get("tool_calls") or "(written as text, parsed by extract_calls)"})
    if len(calls) > 1:
        tag("4 YOUR CODE", "the model asked for %d calls; this mini-lab runs only the first" % len(calls))
    messages.append({"role": "assistant", "content": msg.get("content", ""),
                     "tool_calls": (msg.get("tool_calls") or [])[:1]})

    # [4] YOUR CODE and [5] FUNCTIONS, exactly once
    name, args = calls[0]["name"], calls[0]["arguments"]
    result, outcome = run_call(name, args)
    base.audit({"lab": "fc", "tool": name, "args": args,
                "refused": None if outcome.startswith("ran") else outcome, "hijack": False})

    # [RESULT BACK]
    messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})
    tag("RESULT BACK", "added as a tool message -> %d messages" % len(messages))

    # [3] LLM, request 2: NO tools offered, so it can only answer
    print("-" * 78)
    t0 = time.time()
    raw2 = llm(messages, tools=[])
    tag("3 LLM", "request 2, %.1f s: your code offered NO tools, so the model can only answer" % (time.time() - t0))
    print("=" * 78)
    tag("FINAL ANSWER")
    show((raw2.get("message", {}).get("content") or "").strip(), 2000)

    print("=" * 78)
    tag("SUMMARY", "1 function call, 2 LLM requests, no loop")
    print("      request 1: %s  ->  %s" % ("%s(%s)" % (name, ", ".join(str(v) for v in args.values())) if isinstance(args, dict) else name, outcome))
    print("      request 2: no tools -> final answer")
    if "validate()" in outcome:
        print("      No retry: one trip only. In lab5_agent_loop.py the model gets another try and fixes it.")
    elif "guard()" in outcome:
        print("      No retry here, and a retry would not help: the recipient is not allowed, whatever the shape.")


if __name__ == "__main__":
    main()
