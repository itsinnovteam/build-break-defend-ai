---
title: Tenable Vulnerability Scanning Operations
classification: internal
allowed_groups: [soc-t1, soc-leads, it-ops, it-helpdesk, engineering]
---
# Tenable Vulnerability Scanning Operations

Northwind uses Tenable to scan servers and workstations for vulnerabilities. This guide explains scan schedules and how findings are handled.

## Scan schedule

Credentialed scans of production servers run every Sunday from 01:00 to 05:00. Workstation agents report daily. Ad hoc scans need approval from the SOC on-call analyst so they do not collide with change windows.

## Triage of critical findings

Findings are prioritised by Tenable VPR score. Any finding with VPR 9.0 or higher must be patched within 7 days on internet-facing hosts and 14 days on internal hosts. IT operations owns patching; the SOC tracks deadlines and escalates misses.

## Risk exceptions process

If a critical finding cannot be patched on time, the system owner submits a risk exception request with a compensating control and an expiry date. Approved exceptions are recorded by SOC leads in a separate restricted register. Ask your SOC lead if you need to know whether an exception exists for a host.
