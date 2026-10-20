---
doc_id: DEVOPS-001
title: Production deployment runbook
department: DevOps
classification: internal
allowed_roles: devops
residency: any
owner: DevOps Platform Team
updated: 2026-06-20
---
# Production deployment runbook

Deployments to production run only through the CI/CD pipeline, never by hand. The
pipeline needs a green build, all tests passing, and an approved change request.

Deploy windows: Monday to Thursday, 10:00 to 16:00. No production deployments on Fridays,
weekends or public holidays, unless it is an emergency change.

Use a canary release: send 10 percent of traffic to the new version for 15 minutes and
watch the error rate and latency dashboards. If the error rate stays under 1 percent,
continue to 100 percent.
