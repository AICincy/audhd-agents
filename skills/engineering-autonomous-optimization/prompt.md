# Autonomous Optimization

## Goal

Design self-tuning systems that optimize within safe boundaries. Autonomy without guardrails is a production incident waiting to happen.

## Rules

- Load KRASS.md before processing
- Every autonomous action has: bounds, circuit breaker, rollback trigger
- Human approval required for: cost changes >20%, architecture changes, data deletion
- Start with manual optimization, automate only proven patterns
- Log every autonomous decision for audit
- No em dashes

## Workflow

1. **Scope**: System, objective function, constraints, current baseline, budget
2. **Design**: Optimization strategy, parameter space, bounds, feedback loop
3. **Guard**: Circuit breakers, approval gates, anomaly detection, rollback triggers
4. **Monitor**: Metrics, alerting thresholds, cost tracking, audit log

## Output JSON

```json
{
  "optimization": {
    "system": "string",
    "objective": "string",
    "strategy": "string",
    "parameters": [
      {
        "name": "string",
        "current": "string",
        "range": "string",
        "step": "string"
      }
    ],
    "guardrails": ["string"],
    "circuit_breakers": ["string"],
    "approval_gates": ["string"],
    "monitoring": "string",
    "rollback": "string"
  }
}
```
