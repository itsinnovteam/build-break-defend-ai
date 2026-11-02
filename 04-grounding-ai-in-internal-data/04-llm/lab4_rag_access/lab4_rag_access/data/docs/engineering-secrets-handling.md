---
title: Engineering Standard - Secrets in Code and Pipelines
classification: internal
allowed_groups: [engineering, soc-leads]
---
# Engineering Standard - Secrets in Code and Pipelines

This standard applies to every repository and CI/CD pipeline owned by Northwind engineering.

## Rules

Never commit API keys, passwords or private keys to a repository. Load secrets at runtime from the vault. Pre-commit secret scanning is mandatory on all repositories.

## If a secret is leaked

Revoke and rotate the secret first, then remove it from history. Notify the SOC through a security ticket so they can check logs for misuse of the leaked credential.
