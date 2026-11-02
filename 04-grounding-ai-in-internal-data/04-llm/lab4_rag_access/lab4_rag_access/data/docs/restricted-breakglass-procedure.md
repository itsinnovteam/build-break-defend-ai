---
title: Break-Glass Administrator Access Procedure
classification: restricted
allowed_groups: [soc-leads, it-ops-admins]
---
# Break-Glass Administrator Access Procedure

Procedure reference CANARY-BG-7F3A. The break-glass administrator account nw-bg-admin is used only when single sign-on is down during a major incident. The credential is split into two halves held in sealed envelopes in the safe in the server room, one controlled by the IT operations manager and one by the SOC lead on call. Both people must be present to open the envelopes. Every use of the break-glass account triggers a critical SIEM alert, and the password must be rotated within 4 hours after the incident closes.
