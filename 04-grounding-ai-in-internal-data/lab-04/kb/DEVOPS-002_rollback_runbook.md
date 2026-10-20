---
doc_id: DEVOPS-002
title: Rollback runbook
department: DevOps
classification: internal
allowed_roles: devops, itops
residency: any
owner: DevOps Platform Team
updated: 2026-06-20
---
# Rollback runbook

Roll back when the error rate goes above 1 percent or p95 latency doubles after a
deployment. Do not wait to find the root cause first.

To roll back, run the rollback-prod stage in the pipeline with the previous release tag.
It redeploys the last known good container image in about 5 minutes. Database migrations
must be backward compatible, so a rollback never needs a database restore.

After a rollback, post in the incident channel and open a problem ticket within 1 day.
