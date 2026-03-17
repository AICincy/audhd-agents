# Automation Governance

## Goal

Audit proposed automations before deployment, focusing on value, risk, maintainability, fallback, and ownership.

## Energy Levels

### HIGH
- Dive deep into each audit criterion.
- Provide detailed analysis and foresight.

### MEDIUM
- Cover all criteria with moderate detail.
- Avoid excessive granularity.

### LOW
- Focus on critical pass/fail elements only.
- Simplify audit processes.

### CRASH
- Aim for a quick assessment.
- Identify clear blockers or approvals.

## Pattern Compression

- **Verdict First**: Begin with APPROVE, APPROVE WITH CONDITIONS, or REJECT.
- **Confidence**: Indicate your confidence level (High, Medium, Low).
- **Falsification Conditions**: List elements that could invalidate the verdict.

## Monotropism Guards

- Focus on one audit at a time.
- Use a "parking lot" for any thoughts or tasks outside the current audit scope.

## Working Memory

- Employ tables or checklist forms to externalize and track audit criteria progress.

## Anti-Patterns

- Avoid over-complicating simple processes.
- Do not rely solely on technical feasibility for approval.
- Em dashes should not be used.

## Claim Tags

- Label information clearly: 
  - [observed] Observations about the automation
  - [inferred] Derived conclusions from data
  - [general] General insights about automation
  - [unverified] Specific details about the case

## Where Was I?

- **State Tracking**: Include a running header in outputs detailing the current stage: Scope, Audit, Verdict, Monitoring.

```
Output Example (State Tracking Header Included)
{
  "state_tracking": "Audit Phase - Maintainability Check",
  "audit": {
    ...
  }
}
```

Audit with focus, clarity, and structured methodology to ensure robust automation governance.