doc_id: PB-VUL-007
title: Tenable Critical Vulnerability Handling Procedure
version: 1.6
status: approved
owner: Vulnerability Management Lead
last_reviewed: 2026-09-10
access: soc-all

# Tenable Critical Vulnerability Handling Procedure

FICTIONAL TRAINING DOCUMENT. Northwind SOC. Not a real procedure.

## Scope

Use this procedure when a Tenable scan reports a vulnerability rated
Critical (CVSS 9.0 or higher) or a vulnerability with VPR 9.0 or higher.

## Prioritisation

- Priority 1: the asset is internet-facing AND the vulnerability is listed in
  the CISA Known Exploited Vulnerabilities (KEV) catalog.
- Priority 2: the asset is internet-facing, not in KEV.
- Priority 3: the asset is internal only.

## Remediation SLA

- Priority 1: patch or apply a compensating control within 72 hours.
- Priority 2: patch within 7 calendar days.
- Priority 3: patch within 30 calendar days.

## Steps

1. Export the finding from Tenable with the plugin ID, asset name, and first
   seen date.
2. Look up the asset owner in the CMDB and confirm whether the asset is
   internet-facing.
3. Check the CVE against the CISA KEV catalog to set the priority.
4. Raise a remediation ticket in category "VUL - Critical" assigned to the
   asset owner, with the SLA due date.
5. After the owner reports the fix, trigger a Tenable rescan of the asset.
   Close the ticket only when the rescan shows the plugin as fixed.

## Exceptions

If the owner cannot meet the SLA, they must file a risk exception approved
by the CISO office. Exceptions expire after 90 days.
