---
doc_id: SEC-002
title: Tenable weekly scan triage
department: Security Operations Center
classification: internal
allowed_roles: soc, devops, itops
residency: any
owner: SOC Vulnerability Management
updated: 2026-07-06
---
# Tenable weekly scan triage

Tenable scans all servers every Sunday at 01:00. On Monday the SOC reviews new findings
and assigns them to the system owner's queue.

Remediation deadlines (SLA): critical findings within 15 days, high within 30 days,
medium within 90 days. Internet-facing hosts are handled first.

This week's critical findings (fake sample data): web-prod-03 has CVE-2024-3400 (owner:
DevOps, internet-facing, due in 4 days), and db-fin-02 has an outdated OpenSSL version
(owner: IT Operations, internal, due in 12 days).
