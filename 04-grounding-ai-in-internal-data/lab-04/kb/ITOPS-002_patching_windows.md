---
doc_id: ITOPS-002
title: Server patching windows
department: IT Operations
classification: internal
allowed_roles: itops, devops
residency: any
owner: IT Operations
updated: 2026-04-18
---
# Server patching windows

Linux and Windows servers are patched every second Saturday of the month, from 22:00 to
02:00. Non-production servers are patched one week earlier, so problems show up first.

Critical security patches (CVSS 9.0 or higher, or listed as known exploited) are applied
within 7 days through an emergency change. Reboots of clustered servers are done one
node at a time. Patch results are checked in the monitoring dashboard the next morning.
