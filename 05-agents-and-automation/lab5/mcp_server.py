"""
mcp_server.py - a tiny MCP-style tool server (stdio JSON-RPC, Python standard library only).

MCP (Model Context Protocol) is an open standard for exposing tools and data to AI apps over
a simple JSON-RPC channel, so the SAME tool server can be reused by any agent or app instead
of re-coding the tools each time. This is a teaching-sized version of that idea.

It reads one JSON-RPC request per line on stdin and writes one JSON response per line on
stdout. It exposes ONLY the read-only tools - a server should never hand out more power than
the client needs (least privilege applies to the server too).

Run it through the client:  python mcp_client.py
"""

import json
import sys

import toolkit

READ_ONLY = ("get_alert", "search_logs", "get_asset_owner", "lookup_ip_reputation")
PROTOCOL = "2024-11-05"


def _result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(request):
    rid = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}
    if method == "initialize":
        return _result(rid, {"protocolVersion": PROTOCOL,
                             "serverInfo": {"name": "lab5-soc-tools", "version": "1.0"},
                             "capabilities": {"tools": {}}})
    if method == "tools/list":
        tools = [toolkit.REGISTRY[n][2]["function"] for n in READ_ONLY]
        return _result(rid, {"tools": [{"name": t["name"], "description": t["description"],
                                        "inputSchema": t["parameters"]} for t in tools]})
    if method == "tools/call":
        name = params.get("name")
        if name not in READ_ONLY:                      # the server enforces its own allowlist
            return _error(rid, -32601, f"tool {name!r} is not exposed by this server")
        try:
            output = toolkit.run_tool(name, params.get("arguments", {}))
            return _result(rid, {"content": [{"type": "text", "text": json.dumps(output)}]})
        except (toolkit.ToolError, TypeError) as exc:
            return _result(rid, {"isError": True,
                                 "content": [{"type": "text", "text": str(exc)}]})
    return _error(rid, -32601, f"unknown method {method!r}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            sys.stdout.flush()
            continue
        response = handle(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
