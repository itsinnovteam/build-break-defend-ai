---
access: all
status: current
---
# Brute-Force Login Runbook
## Detection
Windows event ID 4625 records a failed logon. Ten or more 4625 events for
one account within five minutes indicates a brute-force attempt. Event ID
4624 after a burst of 4625 events may mean the attacker succeeded.
## Response
Block the source IP on the firewall, lock the targeted account, and check
for a successful 4624 logon from the same source.
