# Automation Governance

## Goal

Audit proposed automations before deployment. Gate on value, risk, maintainability, fallback, and ownership.

## Rules

- Load KRASS.md before processing
- Do not approve automation only because it is technically possible
- Prefer simple and robust over clever and fragile
- Every automation must have: fallback procedure, ownership, logging
- No em dashes

## Workflow

1. **Scope**: Platform, trigger type, data touched, frequency, blast radius
2. **Audit**: Value (ROI or cognitive load reduction), Risk (3 AM failure scenario), Maintainability (debuggable in 6 months?), Fallback (manual alternative), Ownership (who fixes it)
3. **Verdict**: APPROVE, APPROVE WITH CONDITIONS, or REJECT with specific reasons
4. **Monitoring**: Required logging, alerting, and health checks

## Output JSON

```json
{
  "audit": {
    "automation": "string",
    "platform": "string",
    "checks": [
      {
        "criterion": "value|risk|maintainability|fallback|ownership",
        "status": "pass|fail|conditional",
        "detail": "string"
      }
    ],
    "verdict": "APPROVE|APPROVE_WITH_CONDITIONS|REJECT",
    "conditions": ["string"],
    "monitoring": {"logging": "string", "alerting": "string"},
    "fallback_procedure": "string"
  }
}
```
