---
doc_id: SEC-001
title: Ransomware first-hour playbook
department: Security Operations Center
classification: confidential
allowed_roles: soc, security-lead
residency: any
owner: SOC Incident Response
updated: 2026-06-30
---
# Ransomware first-hour playbook (SOC)

Minute 0 to 15: confirm the alert in the EDR console, isolate the affected hosts with EDR
network containment, and open a P1 incident in the SOC case queue.

Minute 15 to 30: call the incident commander on the SOC on-call line, disable the user
accounts involved, and preserve evidence: take a memory capture before any reboot.

Minute 30 to 60: confirm the backups are intact and offline, block the attacker IP
addresses at the firewall, and brief IT management. Never pay or contact the attacker
without approval from the CISO and Legal.
