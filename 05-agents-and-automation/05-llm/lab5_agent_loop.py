#!/usr/bin/env python3
"""
Lab - The agent loop (continues the function-calling mini-lab; slide 10 diagram, live).
AI Bootcamp, Module 5: Agents and Automation.

The mini-lab showed ONE function call. This lab shows the LOOP around it.
Every line is tagged with the step on the agent-loop diagram:
  [1 GOAL IN]  [2 THINK]  [3 ACT]  [4 OBSERVE]  [5 REPEAT]  [6 STOP]

Reuses the mini-lab's Pydantic classes, validate() and guard() from lab5_function_calling.py.
Python 3.9+, pydantic 2.13.5 (pip install "pydantic==2.13.5" inside a venv,
or pip3 install --user "pydantic==2.13.5" without one).

  python lab5_agent_loop.py --offline                       # NW-4471: the path from the mini-lab
  python lab5_agent_loop.py --offline --alert NW-4475       # a benign alert: the model takes a shorter path
  python lab5_agent_loop.py --offline --max-steps 3         # your code stops the loop
  python lab5_agent_loop.py --offline --alert NW-4475 --workflow   # same task as a fixed workflow
  python lab5_agent_loop.py                                 # real run with Ollama
"""
import argparse
import json
import re
import time
from typing import Any, Dict, List

import lab5_agent as base
import lab5_function_calling as fc      # Pydantic classes, validate(), guard(), FUNCTIONS, TOOL_LIST


def tag(step: str, text: str = "") -> None:
    print("[%s] %s" % (step, text))


def ctx_size(messages: List[Dict[str, Any]]) -> int:
    """Characters the model must read on this step: every message + every tool schema."""
    return len(json.dumps(messages)) + len(json.dumps(fc.TOOL_LIST))


def call_text(name: str, args: Any) -> str:
    if isinstance(args, dict):
        vals = [str(v) if len(str(v)) <= 32 else str(v)[:29] + "..." for v in args.values()]
        if name == "send_email":
            vals = vals[:1] + ["..."]                    # recipient is what matters; body is long
        return "%s(%s)" % (name, ", ".join(vals))
    return "%s(%s)" % (name, args)


def summarise(name: str, result: Any) -> str:
    """One line per observation: what the model learned from this trip."""
    if isinstance(result, dict) and "error" in result:
        d = result.get("details", [{}])[0]
        return "validate() rejected it: %s" % d.get("problem", result["error"])
    if isinstance(result, dict) and "refused" in result:
        return "guard() rejected it: %s" % result["refused"]
    if name == "get_alert":
        ip = re.search(r"(\d+\.\d+\.\d+\.\d+(:\d+)?)", result.get("detail", ""))
        return "%s on %s -> %s" % (result.get("title"), result.get("host"), ip.group(1) if ip else "?")
    if name == "lookup_ip":
        return "%s (%s)" % (result.get("verdict"), ", ".join(result.get("tags", [])))
    if name == "get_tenable_findings":
        if not result:
            return "no findings"
        worst = sorted(result, key=lambda f: -f.get("cvss", 0))[0]
        return "%d finding(s), worst: %s (%s, %s days)" % (len(result), worst["name"], worst["severity"], worst["age_days"])
    if name == "send_email":
        return "email sent to %s" % result.get("to")
    return json.dumps(result)[:80]


# ---------------------------------------------------------------- offline model replies
def scripted(alert: str, to: str):
    """--offline: replays what llama3.1:8b typically does. NW-4471 includes one bad call (the port)."""
    def call(name, **args):
        return {"message": {"role": "assistant", "content": "",
                            "tool_calls": [{"function": {"name": name, "arguments": args}}]}, "eval_count": 26}
    if alert == "NW-4471":
        replies = iter([
            call("get_alert", alert_id="NW-4471"),
            call("lookup_ip", ip="203.0.113.66:443"),        # copied from the alert text: rejected
            call("lookup_ip", ip="203.0.113.66"),            # the retry the mini-lab never got
            call("get_tenable_findings", host="FIN-LT-022"),
            call("send_email", to=to, subject="NW-4471 triage: HIGH",
                 body="FIN-LT-022 beacons to known C2 203.0.113.66 every 60 s; critical VPN client RCE unpatched. "
                      "Recommend isolate, block IP, patch."),
            None,
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
    replies = iter([
        call("get_alert", alert_id="NW-4475"),
        call("lookup_ip", ip="192.0.2.10"),
        call("send_email", to=to, subject="NW-4475 triage: LOW",
             body="OPS-WS-014 sends SMTP to 192.0.2.10, the Northwind mail relay (benign). No action needed."),
        {"message": {"role": "assistant", "content":
            "Severity: LOW. OPS-WS-014 (a.cruz) runs smtpclient.exe sending mail every 15 minutes to "
            "192.0.2.10, the Northwind mail relay, which threat intel marks benign. Expected behaviour; close "
            "as benign. Summary emailed to the SOC lead."}, "eval_count": 70},
    ])
    return lambda messages: next(replies)


# ---------------------------------------------------------------- one trip: ACT + OBSERVE (the mini-lab's box 4 and 5)
def act_and_observe(name: str, args: Any, messages: List[Dict[str, Any]], observations: List[str]) -> str:
    obj, error = fc.validate(name, args)
    if error:
        tag("3 ACT", "validate(): REJECTED by your code. %s does not run." % name)
        result = error  # type: Any
        outcome = "rejected"
    else:
        clean = obj.model_dump(mode="json")
        reason = fc.guard(name, clean)
        if reason:
            tag("3 ACT", "validate(): OK  guard(): REJECTED by your code - " + reason)
            result, outcome = {"refused": reason}, "rejected"
        else:
            result = fc.FUNCTIONS[name][0](**clean)
            tag("3 ACT", "validate(): OK  guard(): allowed  ->  ran %s()" % name)
            outcome = "ran"
    messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})
    line = summarise(name, result)
    observations.append("%s -> %s" % (call_text(name, args), line))
    tag("4 OBSERVE", "%s  (added as message %d)" % (line, len(messages)))
    base.audit({"lab": "loop", "tool": name, "args": args, "refused": None if outcome == "ran" else line, "hijack": False})
    return outcome


# ---------------------------------------------------------------- the agent loop
def run_agent(alert: str, to: str, max_steps: int, offline: bool) -> List[List[str]]:
    llm = scripted(alert, to) if offline else fc.call_llm
    messages = [{"role": "system", "content": "You are Nova, the Northwind SOC night-shift assistant. Use the tools "
                                              "to investigate. Then email a short summary and give your triage: "
                                              "severity, evidence, actions."},
                {"role": "user", "content": "Triage %s and email a two-line summary to %s." % (alert, to)}]
    tag("1 GOAL IN", messages[1]["content"])
    tag("1 GOAL IN", "plus the system prompt and %d tool schemas -> %d messages, ~%d tokens"
        % (len(fc.TOOL_LIST), len(messages), ctx_size(messages) // 4))
    observations, rows = [], []  # type: List[str], List[List[str]]

    for step in range(1, max_steps + 1):
        print("-" * 78)
        before = len(messages)
        chars = ctx_size(messages)
        tag("2 THINK", "step %d of %d. The LLM re-reads everything: %d messages, ~%d tokens%s"
            % (step, max_steps, before, chars // 4, "" if observations else " (no results yet)"))
        for o in observations:
            print("        sees: " + o)
        t0 = time.time()
        raw = llm(messages)
        msg = raw.get("message", {})
        real_tokens = raw.get("prompt_eval_count")
        calls = base.extract_calls(msg)
        if real_tokens:
            tag("2 THINK", "Ollama reports %s prompt tokens, %.1f s" % (real_tokens, time.time() - t0))

        if not calls:
            tag("2 THINK", "decided: no tool call -> answer")
            tag("6 STOP", "the model answered in plain text. Loop ends after %d steps." % step)
            print("=" * 78)
            print((msg.get("content") or "").strip())
            rows.append([str(step), str(before), str(chars // 4), "answer", "-"])
            return rows

        messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": msg.get("tool_calls") or []})
        for c in calls:
            tag("2 THINK", "decided: call " + call_text(c["name"], c["arguments"]))
            outcome = act_and_observe(c["name"], c["arguments"], messages, observations)
            rows.append([str(step), str(before), str(chars // 4), call_text(c["name"], c["arguments"]), outcome])
        tag("5 REPEAT", "context grew %d -> %d messages. Back to THINK." % (before, len(messages)))

    print("-" * 78)
    tag("6 STOP", "step budget of %d reached. Your code stopped the loop: no final answer." % max_steps)
    rows.append([str(max_steps + 1), str(len(messages)), str(ctx_size(messages) // 4), "(budget hit)", "-"])
    return rows


# ---------------------------------------------------------------- the same task as a fixed workflow
def run_workflow(alert: str, to: str) -> List[List[str]]:
    """No LLM decisions: your code fixes the order. Same tools, same validate()/guard()."""
    tag("1 GOAL IN", "Triage %s (workflow: the steps are written in code, the model chooses nothing)" % alert)
    messages, observations, rows = [], [], []  # type: List[Dict[str, Any]], List[str], List[List[str]]
    a = base.get_alert(alert)
    ip = re.search(r"(\d+\.\d+\.\d+\.\d+)", a.get("detail", ""))
    plan = [("get_alert", {"alert_id": alert}),
            ("lookup_ip", {"ip": ip.group(1) if ip else ""}),
            ("get_tenable_findings", {"host": a.get("host", "")}),
            ("send_email", {"to": to, "subject": "%s triage" % alert, "body": "See the triage notes."})]
    for step, (name, args) in enumerate(plan, 1):
        print("-" * 78)
        tag("2 THINK", "step %d: none - the code says %s next" % (step, name))
        outcome = act_and_observe(name, args, messages, observations)
        rows.append([str(step), "-", "-", call_text(name, args), outcome])
    print("-" * 78)
    tag("6 STOP", "end of the fixed list: always %d steps, always this order, 0 LLM calls." % len(plan))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="The agent loop, step by step")
    ap.add_argument("--alert", choices=["NW-4471", "NW-4475"], default="NW-4471")
    ap.add_argument("--to", default="soc-lead@northwind.example")
    ap.add_argument("--max-steps", type=int, default=8, help="step budget (your code enforces it)")
    ap.add_argument("--offline", action="store_true", help="scripted model replies (no Ollama)")
    ap.add_argument("--workflow", action="store_true", help="run the same task as a fixed workflow")
    a = ap.parse_args()
    print("=" * 78)
    rows = run_workflow(a.alert, a.to) if a.workflow else run_agent(a.alert, a.to, a.max_steps, a.offline)
    print("=" * 78)
    tag("LOOP SUMMARY", "one row per trip around the loop")
    print("      %-5s %-9s %-8s %-46s %s" % ("step", "messages", "~tokens", "THINK decided", "ACT"))
    for r in rows:
        print("      %-5s %-9s %-8s %-46s %s" % (r[0], r[1], r[2], r[3][:46], r[4]))
    path = " -> ".join(("BUDGET HIT" if r[3] == "(budget hit)" else r[3].split("(")[0])
                       + ("(x)" if r[4] == "rejected" else "") for r in rows)
    tag("PATH", path)


if __name__ == "__main__":
    main()
