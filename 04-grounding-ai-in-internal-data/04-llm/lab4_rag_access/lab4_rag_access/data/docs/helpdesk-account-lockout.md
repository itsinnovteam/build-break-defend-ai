---
title: Helpdesk Guide - Account Lockouts and Password Resets
classification: internal
allowed_groups: [it-helpdesk, soc-t1, soc-leads]
---
# Helpdesk Guide - Account Lockouts and Password Resets

Use this guide when a user calls about a locked account or a forgotten password.

## Verify the caller

Before any reset, verify the caller with a call-back to the phone number in the HR directory. Never reset based on a phone number the caller gives you. Ask the user to approve an MFA push as a second check.

## Unlock or reset

Unlock the account in the identity console. For a password reset, issue a one-time temporary password that expires in 24 hours and require a change at next sign-in.

## When to involve the SOC

Open a SOC ticket if the account locked more than 3 times in a day, if the user did not cause the lockout, or if the user reports MFA prompts they did not request. These are common signs of password spraying or MFA fatigue attacks.
