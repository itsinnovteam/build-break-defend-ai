"""
tool_demo.py - Section 1: one tool-calling round trip, shown in full.

Tool (function) calling is three steps:
  1. We send the model a task AND a list of tools it may ask for (name, description, schema).
  2. The model replies with a request to CALL one tool, with arguments. It does not run it.
  3. OUR CODE runs the tool and sends the result back, so the model can use it.

This script does exactly one round trip and prints each part, so you can see the shape of
a tool call before the agent loop in Section 2 repeats it many times.

Run:  python tool_demo.py
"""

import json
import sys

import ollama_client
import toolkit


def main():
    tools = toolkit.schemas_for(["lookup_ip_reputation", "get_asset_owner"])
    messages = [
        {"role": "system", "content": "You are a SOC assistant. Use a tool to answer."},
        {"role": "user", "content": "Is the IP 198.51.100.20 malicious?"},
    ]
    print("1. We send the task and the tools the model MAY use:")
    for t in tools:
        print(f"     tool: {t['function']['name']}({', '.join(t['function']['parameters']['properties'])})")
    print(f'     task: "{messages[-1]["content"]}"\n')

    try:
        message, usage = ollama_client.chat(messages, tools=tools)
    except ollama_client.OllamaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    calls = message.get("tool_calls") or []
    if not calls:
        print("2. The model answered directly (no tool call):")
        print("     " + message.get("content", "").strip())
        return 0

    call = calls[0]["function"]
    print("2. The model did NOT run anything. It asked us to call a tool:")
    print(f"     {call['name']}({json.dumps(call['arguments'])})\n")

    print("3. OUR CODE decides to run it, and sends the result back:")
    try:
        result = toolkit.run_tool(call["name"], call["arguments"])
        print(f"     result: {json.dumps(result)}")
    except (toolkit.ToolError, TypeError) as exc:
        print(f"     refused: {exc}")
    print("\nThat is the whole mechanism. The model proposes; your code disposes. Section 5.5")
    print("(and Lab 5) is about making step 3 safe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
