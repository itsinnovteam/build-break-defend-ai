---
access: all
status: current
---
# Phishing Response Playbook (v3, 2026)
## Triage
Check the sender domain, links and attachments in the sandbox. If a user
clicked a link, reset the user's password and revoke active sessions.
## Containment
Block the sender domain and the URL on the mail gateway and web proxy.
Search all mailboxes for the same subject line and purge matching messages.
## Escalation
Escalate to tier 2 if credentials were entered or an attachment was opened.
