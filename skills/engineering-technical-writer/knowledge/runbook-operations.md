---
title: Runbook and Operations Documentation
domain: technical-writing
subdomain: operations
audience: SRE, DevOps, on-call engineers, technical writers
tags: [runbook, incident, operations, playbook, sre, monitoring]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Runbook and Operations Documentation

## Purpose

Provide reusable patterns for writing runbooks, incident playbooks, and operational documentation. Runbooks must be executable under stress: clear steps, no ambiguity, testable verification. [general]

## Runbook Types

| Type | Purpose | Trigger | Audience |
| --- | --- | --- | --- |
| Alert Runbook | Respond to a specific alert | Monitoring alert fires | On-call engineer |
| Deployment Runbook | Execute a release | Scheduled release window | DevOps engineer |
| Incident Playbook | Manage a live incident | SEV-1 or SEV-2 declared | Incident commander |
| Recovery Runbook | Restore from failure | System outage detected | SRE |
| Maintenance Runbook | Perform routine maintenance | Scheduled maintenance window | Operations team |

## Alert Runbook Template

```markdown
# Runbook: [Alert Name]

## Alert Details
- **Alert**: [Exact alert name from monitoring system]
- **Severity**: [SEV-1 | SEV-2 | SEV-3 | SEV-4]
- **Service**: [Service name]
- **Dashboard**: [Link to dashboard]
- **Escalation**: [Team or person to escalate to]

## Symptoms
- [What the alert indicates]
- [What users may experience]

## Diagnosis Steps

1. Check the dashboard: [link]
   - Expected: [normal range]
   - If abnormal: proceed to step 2
2. Query recent logs:
   ```bash
   kubectl logs -l app=my-service --since=10m | grep ERROR
   ```
   - Expected: fewer than 5 errors per minute
   - If elevated: proceed to step 3
3. Check upstream dependencies:
   ```bash
   curl -s https://api.dependency.example.com/healthz
   ```
   - Expected: HTTP 200
   - If failing: see [Upstream Dependency Runbook]

## Resolution Steps

1. [Specific action with exact command]
   ```bash
   kubectl rollout restart deployment/my-service -n production
   ```
2. Verify resolution:
   ```bash
   kubectl rollout status deployment/my-service -n production
   ```
   - Expected: "successfully rolled out"
3. Monitor for 10 minutes. Confirm alert clears.

## Escalation
- If unresolved after 15 minutes: page [Team Lead]
- If data loss suspected: invoke [Incident Playbook]

## Post-Incident
- [ ] Update this runbook with lessons learned
- [ ] File ticket for root cause investigation
```

## Runbook Writing Rules

1. Every step must be a concrete action, not a suggestion. "Restart the service" not "Consider restarting". [general]
2. Every command must be copy-pasteable. Include the full command with flags and paths. [observed]
3. Every step must have a verification: expected output or condition to check. [general]
4. Include exact dashboard links, not "check the dashboard". [observed]
5. Write for 3 AM comprehension: short sentences, numbered steps, no jargon without definitions. [general]
6. Include time limits: "If not resolved in 15 minutes, escalate." [general]
7. Test runbooks quarterly by having someone unfamiliar execute them. [observed]

## Incident Playbook Template

```markdown
# Incident Playbook: [Incident Type]

## Classification
- **Severity**: [SEV-1 | SEV-2]
- **Impact**: [User-facing | Internal | Data integrity]
- **SLO at risk**: [Which SLO and current burn rate]

## Roles
| Role | Responsibility | Contact |
| --- | --- | --- |
| Incident Commander | Coordinates response, communicates status | [Name/rotation] |
| Technical Lead | Diagnoses and fixes | [Name/rotation] |
| Communications | Updates stakeholders | [Name/rotation] |

## Timeline Template
| Time | Action | Owner |
| --- | --- | --- |
| T+0 | Incident declared, roles assigned | IC |
| T+5 | Initial diagnosis complete | Tech Lead |
| T+15 | First status update to stakeholders | Comms |
| T+30 | Escalate if unresolved | IC |

## Communication Templates

### Internal Status Update
```
INCIDENT: [Title]
SEVERITY: [SEV-X]
STATUS: [Investigating | Identified | Monitoring | Resolved]
IMPACT: [What is affected]
NEXT UPDATE: [Time]
```

### External Status Update
```
We are aware of an issue affecting [service].
[X]% of users may experience [symptom].
Our team is actively investigating.
Next update at [time].
```

## Deployment Runbook Template

```markdown
# Deployment: [Service] v[Version]

## Pre-Deployment Checklist
- [ ] All tests passing on release branch
- [ ] Database migrations reviewed and tested
- [ ] Rollback plan documented below
- [ ] Stakeholders notified of maintenance window

## Deployment Steps

1. Enable maintenance mode:
   ```bash
   kubectl annotate deployment/my-service maintenance=true
   ```
2. Run database migrations:
   ```bash
   python manage.py migrate --database=production
   ```
   - Verify: `python manage.py showmigrations | grep "\[X\]"`
3. Deploy new version:
   ```bash
   kubectl set image deployment/my-service app=registry/my-service:v1.2.0
   ```
4. Verify deployment:
   ```bash
   kubectl rollout status deployment/my-service
   curl -s https://api.example.com/healthz | jq .version
   ```
   - Expected: `"1.2.0"`
5. Disable maintenance mode:
   ```bash
   kubectl annotate deployment/my-service maintenance-
   ```
6. Run smoke tests:
   ```bash
   python scripts/smoke_test.py --env production
   ```

## Rollback Plan

1. Roll back deployment:
   ```bash
   kubectl rollout undo deployment/my-service
   ```
2. Roll back migrations (if applied):
   ```bash
   python manage.py migrate myapp 0042 --database=production
   ```
3. Verify rollback:
   ```bash
   curl -s https://api.example.com/healthz | jq .version
   ```
```

## Monitoring Documentation

### Alert Definition Template

| Field | Value |
| --- | --- |
| Alert name | [Descriptive name] |
| Metric | [Exact metric name and source] |
| Condition | [Threshold, window, aggregation] |
| Severity | [SEV level] |
| Runbook | [Link to runbook] |
| Notification | [Channel, team, escalation] |

### Dashboard Documentation

Each dashboard should have a companion document: [general]
- Purpose of the dashboard
- What each panel shows and why it matters
- Normal ranges for key metrics
- Link to relevant runbooks when metrics go abnormal

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| "Check the logs" without a query | Engineer does not know what to search for | Provide exact log query |
| Steps without verification | No way to confirm action succeeded | Add expected output after each step |
| Runbook requires tribal knowledge | Fails when the expert is unavailable | Write for someone unfamiliar |
| Untested runbooks | Steps may be outdated or wrong | Quarterly runbook drills |
| Missing escalation criteria | Engineer does not know when to ask for help | Include time limits and escalation paths |

## Grounding Checklist

Before publishing operational documentation, verify: [observed]
- [ ] Every step has a concrete, copy-pasteable command
- [ ] Every step has expected output or verification criteria
- [ ] Escalation path includes time limits and contact info
- [ ] Dashboard and monitoring links are current and accessible
- [ ] Runbook has been tested by someone who did not write it
- [ ] Rollback procedures are documented for every deployment step
- [ ] Communication templates exist for internal and external updates
