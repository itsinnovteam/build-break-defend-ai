"""
mcp_client.py - talk to mcp_server.py over stdio JSON-RPC (Python standard library only).

It launches the server as a subprocess, does the MCP handshake (initialize), lists the
tools the server offers (tools/list), and calls one (tools/call). This is the same shape
as a real MCP client talking to a real MCP server - just small enough to read in full.

Run:  python mcp_client.py
"""

import json
# subprocess is used only to launch our own MCP server (fixed command, no shell, no user input).
import subprocess  # nosec B404
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


class MCPClient:
    def __init__(self, server=HERE / "mcp_server.py"):
        # Fixed, trusted command (our own interpreter + our own server file), no shell,
        # no user input. Reviewed and accepted, and marked on the next line for the scanner.
        self.proc = subprocess.Popen(  # nosec B603
            [sys.executable, str(server)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=str(HERE))
        self._id = 0

    def call(self, method, params=None):
        self._id += 1
        request = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("the MCP server stopped responding")
        reply = json.loads(line)
        if "error" in reply:
            raise RuntimeError(reply["error"]["message"])
        return reply["result"]

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main():
    client = MCPClient()
    try:
        info = client.call("initialize", {"protocolVersion": "2024-11-05"})
        print(f"Connected to MCP server: {info['serverInfo']['name']} v{info['serverInfo']['version']}")
        tools = client.call("tools/list")["tools"]
        print(f"\nTools this server offers ({len(tools)}):")
        for t in tools:
            print(f"  - {t['name']}: {t['description']}")
        print("\nCalling lookup_ip_reputation for 198.51.100.20 ...")
        out = client.call("tools/call", {"name": "lookup_ip_reputation",
                                         "arguments": {"ip": "198.51.100.20"}})
        print("  result:", out["content"][0]["text"])
        print("\nAsking for a tool the server does NOT expose (disable_account) ...")
        out = client.call("tools/call", {"name": "disable_account", "arguments": {"account": "svc-backup"}})
        print("  result:", out)
    except RuntimeError as exc:
        print(f"  refused: {exc}")
    finally:
        client.close()
    print("\nThe server offers only read-only tools. The dangerous tools are not reachable "
          "through MCP at all - least privilege at the server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
