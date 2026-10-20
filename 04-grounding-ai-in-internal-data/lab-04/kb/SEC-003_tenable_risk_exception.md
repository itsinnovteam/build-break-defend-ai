---
doc_id: SEC-003
title: Tenable risk exception process
department: Security Operations Center
classification: internal
allowed_roles: soc, devops
residency: any
owner: SOC Vulnerability Management
updated: 2026-05-28
---
# Tenable risk exception process

Sometimes a vulnerability cannot be fixed in time, for example when the vendor has no
patch yet. Then the system owner can request a risk exception (risk acceptance).

Who approves: the Head of SOC and the system owner must both approve. An exception lasts
at most 90 days; for critical findings the maximum is 30 days. Every exception needs a
compensating control, such as a firewall rule or extra monitoring, and a ticket in the
SEC-EXC queue. Expired exceptions reopen automatically in Tenable.
