---
access: all
status: current
---
# Ransomware Response Playbook
## Detection
EDR alerts for mass file renaming, shadow copy deletion (vssadmin delete
shadows) or a ransom note file indicate possible ransomware.
## Containment
Disconnect the infected host from the network immediately, but do not
power it off: memory holds encryption keys and evidence. Isolate the host
in EDR network containment mode and disable the affected user account.
## Eradication
Re-image the host from a known-good image. Rotate credentials used on it.
## Recovery
Restore files from the last clean backup and monitor the host for 14 days.
