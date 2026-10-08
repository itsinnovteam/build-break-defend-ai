# SPEC – what triage_tool.py MUST do

This is the contract. The AI's code, your fix, and your tests are all judged
against these rules. Keep every function name and parameter exactly as listed.

| # | Function | Required behaviour |
|---|----------|--------------------|
| R1 | `parse_failed_logins(lines)` | Return `{ip: count}`. Count **every** line with `Failed password for <user> from <ip>` **including** `Failed password for invalid user <user> from <ip>`. Ignore all other lines. |
| R2 | `is_brute_force(count, threshold=5)` | Return `True` when `count` is **5 or more** (`count >= threshold`). |
| R3 | `is_valid_ip(ip)` | Return `True` only for a real IPv4 address (four numbers, each 0–255). Return `False` for anything else (e.g. `999.1.1.1`, `1.2.3`, `abc`, `1.2.3.4; rm -rf /`, and IPv6 addresses such as `::1`). Never raise. |
| R4 | `lookup_user(conn, username)` | Return `(username, department)` or `None`. Must use a **parameterized** SQL query. Input like `x' OR '1'='1` must return `None`. |
| R5 | `check_reputation(ip, feed)` | Return `feed[ip]` if the IP is in the feed. If the IP is **not** in the feed, or the feed is `None`, return `"unknown"`. Never return `"clean"` by default (fail **closed**). |
| R6 | `build_intel_request(ip)` | Read the token from the environment variable `THREAT_INTEL_TOKEN` each time the function is called (not once when the file is imported). If it is not set, raise `RuntimeError`. No token may be written in the source code. |
| R7 | `block_ip(ip, blocklist_path="blocklist.txt")` | If `ip` is not valid (R3), raise `ValueError` and write nothing. Otherwise append the line `BLOCK <ip>` to the file. Must **not** use a shell. |
