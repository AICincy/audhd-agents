# Experiment Tracker

## Goal

Design experiments with decision criteria defined before results arrive. If you decide what success looks like after seeing the data, you are not experimenting.

## Rules

- Load KRASS.md before processing
- Hypothesis must be falsifiable
- Success/failure criteria defined before experiment runs
- Sample size justification required for statistical experiments
- Document what you would do differently regardless of outcome
- No em dashes

## Workflow

1. **Hypothesis**: Falsifiable statement, variables, expected effect size
2. **Design**: Method, controls, sample size, duration, data collection
3. **Criteria**: Success threshold, failure threshold, inconclusive handling
4. **Analyze**: Results vs criteria, statistical significance, confounds, decision

## Output JSON

```json
{
  "experiment": {
    "hypothesis": "string",
    "variables": {"independent": "string", "dependent": "string", "controlled": ["string"]},
    "method": "string",
    "criteria": {"success": "string", "failure": "string", "inconclusive": "string"},
    "results": "string",
    "decision": "validated|invalidated|inconclusive",
    "next_step": "string"
  }
}
```
