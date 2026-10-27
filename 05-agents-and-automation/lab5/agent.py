"""
agent.py - the agent loop, in two versions side by side.

An AGENT is a loop: the model THINKS, asks to CALL A TOOL, we run it and give back the
RESULT (the observation), and the model thinks again - until it has an answer or we stop it.

  Policy.naive()    v1: every tool available, output trusted, no approval  -> hijackable
  Policy.defended() v2: least-privilege allowlist, output treated as data, approval for
                        write/external actions, step limit, full audit   -> safe

The security rule of the whole module: the MODEL only ever RETURNS a request to call a tool.
OUR CODE (handle_call below) decides whether it actually runs. That is the trust boundary.
"""

import datetime
import json
import os

import config
import safety
import toolkit


def default_validate(name, args):
    """Business rules for a dangerous action, applied in v2 AFTER a human approves.
    Returns None if the arguments are allowed, or a string reason to refuse."""
    if name == "send_email":
        domain = str(args.get("to", "")).split("@")[-1].lower()
        if domain not in config.EMAIL_ALLOWED_DOMAINS:
            return f"recipient {args.get('to')!r} is not internal (allowed: {', '.join(config.EMAIL_ALLOWED_DOMAINS)})"
    if name == "disable_account":
        try:
            info = toolkit.get_asset_owner(args.get("account", ""))
        except toolkit.ToolError:
            info = {}
        if info.get("critical") or "do not disable" in info.get("note", "").lower():
            return f"{args.get('account')!r} is a critical account and must not be disabled by the agent"
    if name == "block_ip":
        ip = str(args.get("ip", ""))
        if not any(ip.startswith(prefix) for prefix in config.BLOCKABLE_IP_RANGES):
            return f"{ip} is outside the ranges the agent may block"
    return None


class Policy:
    def __init__(self, name, allowlist, approve, treat_output_as_data, require_approval,
                 system_prompt, validate=None):
        self.name = name                         # "v1" or "v2"
        self.allowlist = allowlist               # tuple of tool names, or None = every tool
        self.approve = approve                   # function(tool_name, args) -> True/False
        self.treat_output_as_data = treat_output_as_data
        self.require_approval = require_approval  # gate write/external tools?
        self.system_prompt = system_prompt
        self.validate = validate                 # function(tool_name, args) -> reason | None

    @staticmethod
    def naive(system_prompt):
        return Policy("v1", None, lambda n, a: True, False, False, system_prompt, validate=None)

    @staticmethod
    def defended(system_prompt, approve=lambda n, a: False, allowlist=config.TRIAGE_ALLOWLIST):
        return Policy("v2", allowlist, approve, True, True, system_prompt, validate=default_validate)

    def tools(self):
        names = self.allowlist if self.allowlist is not None else toolkit.tool_names()
        return list(names), toolkit.schemas_for(names)


def handle_call(policy, name, args):
    """
    THE TRUST BOUNDARY. Decide what happens to one tool call the model asked for.
    Returns (decision, detail): decision is 'ran' | 'blocked' | 'denied' | 'error'.
    """
    if policy.allowlist is not None and name not in policy.allowlist:
        return "blocked", f"tool '{name}' is not allowed for this task (least privilege)"
    risk = toolkit.risk_of(name)
    if risk is None:
        return "blocked", f"unknown tool '{name}'"
    if policy.require_approval and risk in config.REQUIRE_APPROVAL \
            and name not in config.AUTO_ALLOWED_WRITES:
        if not policy.approve(name, args):
            return "denied", f"a human did not approve this {risk} action"
    if policy.validate is not None:
        reason = policy.validate(name, args)
        if reason:
            return "blocked", f"argument check failed: {reason}"
    try:
        return "ran", toolkit.run_tool(name, args)
    except (toolkit.ToolError, TypeError) as exc:
        return "error", str(exc)


def _observation_text(policy, decision, detail):
    payload = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
    if decision != "ran":
        payload = f"[{decision}] {payload}"
    return safety.wrap_observation(payload) if policy.treat_output_as_data else payload


def run(task, chat_fn, policy, max_steps=None):
    """
    Run the agent loop. chat_fn(messages, tools) -> (reply_message, usage).
    Returns a result dict with the full transcript.
    """
    max_steps = max_steps or config.MAX_STEPS
    names, schemas = policy.tools()
    messages = [{"role": "system", "content": policy.system_prompt},
                {"role": "user", "content": task}]
    r = {"version": policy.name, "task": task, "tools_available": names,
         "steps": [], "final": None, "stopped": None, "messages": messages}
    calls = 0
    for step in range(1, max_steps + 1):
        message, _ = chat_fn(messages, schemas)
        messages.append({"role": "assistant", "content": message.get("content", ""),
                         "tool_calls": message.get("tool_calls", [])})
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            r["final"] = safety.clean_for_terminal(message.get("content", "")).strip()
            r["stopped"] = "answered"
            return r
        for call in tool_calls:
            calls += 1
            if calls > config.MAX_TOOL_CALLS:
                r["stopped"] = "tool-call-limit"
                r["final"] = "Stopped: too many tool calls."
                return r
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            decision, detail = handle_call(policy, name, args)
            injection = safety.find_injection(json.dumps(detail, ensure_ascii=False)) if decision == "ran" else []
            r["steps"].append({"step": step, "tool": name, "args": args,
                               "risk": toolkit.risk_of(name), "decision": decision,
                               "detail": detail, "injection_in_result": injection})
            messages.append({"role": "tool", "content": _observation_text(policy, decision, detail)})
    r["stopped"] = "step-limit"
    r["final"] = "Stopped: reached the step limit without a final answer."
    return r


# ---------- audit + printing --------------------------------------------------
def write_audit(r, path=None):
    """One JSON line per tool call: who, which tool, decision, result status. No secrets."""
    path = path or config.AUDIT_FILE
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        for s in r["steps"]:
            line = {
                "time_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "version": r["version"], "tool": s["tool"], "risk": s["risk"],
                "decision": s["decision"],
                "result": "ok" if s["decision"] == "ran" else s["decision"],
                "injection_flagged": bool(s["injection_in_result"]),
            }
            f.write(json.dumps(line) + "\n")
    if new:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def danger_calls(r, true_task_tools=config.TRIAGE_ALLOWLIST):
    """Tool calls that actually RAN and are a write/external action outside the triage job.
    This is how we measure a hijack without needing the real model."""
    bad = []
    for s in r["steps"]:
        if s["decision"] == "ran" and s["risk"] in (config.WRITE, config.EXTERN) \
                and s["tool"] not in true_task_tools:
            bad.append((s["tool"], s["args"]))
    return bad
