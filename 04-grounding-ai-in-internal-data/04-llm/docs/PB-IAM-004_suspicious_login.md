doc_id: PB-IAM-004
title: Suspicious Login and Account Compromise Playbook
version: 3.2
status: approved
owner: SOC Tier 2 Lead
last_reviewed: 2026-08-14
access: soc-all

# Suspicious Login and Account Compromise Playbook

FICTIONAL TRAINING DOCUMENT. Northwind SOC. Not a real procedure.

## Scope

Use this playbook when the SIEM raises any of these alerts: multiple failed
logins followed by a successful login, a successful login from an unusual
country, or impossible travel (two logins from locations too far apart for the
time between them).

## Severity criteria

- Critical: the account is a privileged account (domain admin, cloud admin,
  or a member of the PAM vault group), OR the login was followed by MFA
  method changes or new mailbox forwarding rules.
- High: a standard user account with a successful login from an unusual
  country and no matching travel record in the HR travel register.
- Medium: failed logins only, with no successful login in the following
  60 minutes.
- Low: the source IP belongs to the corporate VPN egress range (see the
  VPN egress list in the SOC wiki).

## Triage steps

1. Confirm the alert is not a known VPN egress IP. If it is, set severity to
   Low and close with reason "Corporate VPN".
2. Run SIEM query Q-IAM-01 to list all logins for the account in the last
   7 days:
   `SigninLogs | where UserPrincipalName == "<user>" | where TimeGenerated > ago(7d) | project TimeGenerated, IPAddress, Location, ResultType, AuthenticationRequirement`
3. Run SIEM query Q-IAM-02 to check for MFA changes and new inbox rules in
   the 24 hours after the successful login:
   `AuditLogs | where TargetResources has "<user>" | where OperationName in ("User registered security info", "New-InboxRule") | where TimeGenerated > ago(1d)`
4. Check the HR travel register for an approved trip that matches the login
   country.
5. Do not contact the user by email. Call the user on the phone number in
   the HR directory to confirm whether the login was theirs.

## Containment

- For High and Critical: revoke all active sessions and force a password
  reset through the identity admin console. Tier 1 may do this without
  approval.
- For Critical: also disable the account. Disabling a privileged account
  requires approval from the on-call Incident Response (IR) Lead.
- Block the source IP on the perimeter firewall only if it appears in two or
  more alerts within 24 hours.

## Escalation path

- Low and Medium: Tier 1 handles and closes. No escalation.
- High: escalate to Tier 2 within 30 minutes. Create a ticket in category
  "IAM - Account Compromise".
- Critical: page the on-call IR Lead within 15 minutes and open a major
  incident bridge. Notify the CISO office if the account has access to
  customer data.
