doc_id: PB-EML-002
title: Phishing Report Triage SOP
version: 2.4
status: approved
owner: SOC Email Security Lead
last_reviewed: 2026-07-02
access: soc-all

# Phishing Report Triage SOP

FICTIONAL TRAINING DOCUMENT. Northwind SOC. Not a real procedure.

## Scope

Use this SOP when a user reports a suspicious email through the "Report
Phish" button or by forwarding it to the phishing mailbox.

## Triage steps

1. Open the reported email in the email security console. Never open links
   or attachments on an analyst workstation; use the sandbox.
2. Check the sender domain age and SPF, DKIM and DMARC results shown in the
   console header view.
3. Submit every URL and attachment to the sandbox and record the verdict in
   the ticket.
4. Run mailbox search query Q-EML-01 to find every other recipient of the
   same message:
   `EmailEvents | where NetworkMessageId == "<id>" or (SenderFromAddress == "<sender>" and Subject == "<subject>") | where Timestamp > ago(3d) | summarize Recipients = make_set(RecipientEmailAddress)`
5. Check whether any recipient clicked the link with query Q-EML-02:
   `UrlClickEvents | where Url has "<domain>" | where Timestamp > ago(3d)`

## Quarantine

- If the sandbox verdict is malicious, quarantine the message from all
  mailboxes found by Q-EML-01 using the "Purge to quarantine" action.
- Add the sender domain to the email block list for 30 days.
- If a user clicked the link, open a second ticket using PB-IAM-004 for that
  user and force a password reset.

## Ticket and response SLA

- Ticket category: "EML - Phishing".
- Acknowledge the reporting user within 1 business hour using template
  T-EML-ACK.
- Malicious with clicks: resolve or escalate to Tier 2 within 4 hours.
- Malicious with no clicks: resolve within 8 business hours.
- Benign or spam: close within 1 business day and thank the reporter.
