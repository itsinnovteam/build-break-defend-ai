---
title: SOC Playbook - Phishing Triage
classification: internal
allowed_groups: [soc-t1, soc-leads]
---
# SOC Playbook - Phishing Triage

Tier 1 analysts use this playbook for every user-reported phish and every mail gateway alert.

## Step 1 - Scope the message

Pull the message headers from the mail gateway. Record sender, return-path, subject and every URL and attachment hash. Search the mail gateway for the same sender or subject in the last 7 days to find other recipients.

## Step 2 - Analyse indicators

Detonate URLs and attachments in the sandbox. Check hashes and domains against threat intelligence. A phish is confirmed when the sandbox shows credential harvesting or malware download.

## Step 3 - Contain

For a confirmed phish, purge the message from all mailboxes, block the sender domain and URLs at the gateway and proxy, and reset passwords for any user who clicked and entered credentials. Escalate to a SOC lead if more than 10 users clicked.
