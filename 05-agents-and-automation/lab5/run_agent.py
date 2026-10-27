"""
run_agent.py - run the SOC triage agent on one alert, with the naive or the defended policy.

Examples:
  python run_agent.py --task "Triage alert A-1007"                 # defended (v2), safe
  python run_agent.py --task "Triage alert A-1007" --version v1    # naive, hijackable
  python run_agent.py --task "Triage alert A-1008"                 # a clean alert

Each AI step takes about 10 to 60 seconds on a CPU. That is normal.
"""

import argparse
import sys

import agent
import config
import ollama_client
import toolkit

RISK_TAG = {config.READ: "", config.WRITE: " (write)", config.EXTERN: " (external!)"}


def make_approver(mode):
    """How a human answers an approval request for a write/external action."""
    if mode == "auto":
        return lambda name, args: True          # DANGER: approve everything (demo only)
    if mode == "deny":
        return lambda name, args: False         # safe default for an unattended run

    def ask(name, args):                        # interactive: ask the operator
        print(f"\n    APPROVAL NEEDED: the agent wants to run {name}({args})")
        try:
            return input("    Allow this action? [y/N] ").strip().lower() in ("y", "yes")
        except EOFError:
            return False
    return ask


def print_result(r, job_tools=config.TRIAGE_ALLOWLIST):
    print(f"Agent {r['version']}   task: {r['task']}")
    print(f"Tools available: {', '.join(r['tools_available'])}")
    print("-" * 70)
    for s in r["steps"]:
        tag = RISK_TAG.get(s["risk"], "")
        mark = {"ran": "ok", "blocked": "BLOCKED", "denied": "DENIED", "error": "error"}[s["decision"]]
        print(f"  step {s['step']}: {s['tool']}{tag}  ->  {mark}")
        if s["decision"] == "ran":
            short = str(s["detail"])
            print(f"           {short[:110]}")
        else:
            print(f"           {s['detail']}")
        if s["injection_in_result"]:
            print(f"           !! the result contains text that tries to instruct the agent: "
                  f"\"{s['injection_in_result'][0]}\" (treated as data, not followed)")
    print("-" * 70)
    danger = agent.danger_calls(r, true_task_tools=job_tools)
    if danger:
        print("HIJACKED: the agent performed actions it was never asked to do:")
        for name, args in danger:
            print(f"  - {name}({args})")
    print(f"\nFinal answer:\n{r['final']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--task", required=True, help='what to do, e.g. "Triage alert A-1007"')
    parser.add_argument("--version", choices=["v1", "v2"], default="v2",
                        help="v1 = naive (hijackable), v2 = defended (default)")
    parser.add_argument("--approve", choices=["deny", "ask", "auto"], default="ask",
                        help="v2 only: how write/external actions are approved (default: ask)")
    parser.add_argument("--job", choices=["triage", "response"], default="triage",
                        help="v2 only: triage = read-only; response = may also block an IP (with approval)")
    args = parser.parse_args(argv)

    system = (config.HERE / "prompts" / f"system_{args.version}.txt").read_text(encoding="utf-8")
    if args.version == "v1":
        policy = agent.Policy.naive(system)
    else:
        allowlist = config.RESPONSE_ALLOWLIST if args.job == "response" else config.TRIAGE_ALLOWLIST
        policy = agent.Policy.defended(system, approve=make_approver(args.approve), allowlist=allowlist)

    def chat_fn(messages, tools):
        return ollama_client.chat(messages, tools=tools)

    try:
        ollama_client.version()
    except ollama_client.OllamaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Running the agent... (each AI step on a CPU can take 10 to 60 seconds)\n")
    r = agent.run(args.task, chat_fn, policy)
    if args.version == "v2":
        agent.write_audit(r)
    job_tools = config.RESPONSE_ALLOWLIST if (args.version == "v2" and args.job == "response") \
        else config.TRIAGE_ALLOWLIST
    print_result(r, job_tools=job_tools)
    return 0


if __name__ == "__main__":
    sys.exit(main())
