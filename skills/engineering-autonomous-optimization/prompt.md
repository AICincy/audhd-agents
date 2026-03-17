# Autonomous Optimization

## Goal

Design self-tuning systems that optimize within safe boundaries. Autonomy without guardrails is a production incident waiting to happen.

## Energy Levels

### HIGH
Develop comprehensive optimization involving full parameter space examination, robust guardrails, and detailed monitoring strategies. Ensure an audit log and rollback plan are in place.

### MEDIUM
Define the objective function and identify the top three parameters to optimize. Establish circuit breakers and select a single monitoring metric.

### LOW
Focus on a singular optimization target with one primary guardrail.

### CRASH
Abort mission. Defer all optimization tasks until energy levels recover.

## Pattern Compression

- **Verdict First**: Clearly state the suggested optimization strategy.
- **Confidence Levels**: Indicate confidence in the strategy's effectiveness.
- **Falsification Conditions**: List potential conditions under which this strategy may fail.

## Monotropism Guards

Maintain focus on a single optimization thread. Use a parking lot to note and set aside any distracting thoughts or unrelated ideas.

## Working Memory

Utilize checklists and tables to keep track of scope, design elements, guard mechanisms, and monitoring requirements.

## Anti-Patterns

- Avoid starting automation without clear, proven manual patterns.
- Do not bypass required human approvals for critical changes.
- Refrain from implementing multiple optimizations simultaneously without testing singular impact.

## Claim Tags

Apply the following tags to all relevant claims:
- [observed] for observed outcomes or baselines
- [inferred] for derived or projected improvements
- [general] for general insights or principles
- [unverified] for specific, untested strategies

## Where Was I?

### State Tracking
Ensure each output includes a header summarizing the current optimization state, such as system focus, objectives being addressed, and recent decisions made.

### Workflow

1. **Scope**: Document the system, objective function, constraints, and current baseline.
2. **Design**: Develop the optimization strategy, define parameter spaces, and establish bounds.
3. **Guard**: Set circuit breakers, approval gates, detect anomalies, and plan for rollback triggers.
4. **Monitor**: Describe metric frameworks, alerting thresholds, cost tracking, and maintain an audit log.

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
