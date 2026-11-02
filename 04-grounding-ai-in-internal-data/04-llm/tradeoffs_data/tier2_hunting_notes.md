---
access: tier2
status: current
---
# Tier 2 Threat Hunting Notes
## Lateral movement
Hunt for pivoting between hosts with remote service creation (event ID
7045) and SMB logons from workstations to other workstations. Check for
C2 beacon callbacks at regular intervals to rare domains.
