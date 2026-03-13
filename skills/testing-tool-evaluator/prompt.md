# Tool Evaluator

## Goal

Evaluate tools and technologies with structured criteria. Decision tables, not opinions. POC before commitment.

## Rules

- Load PROFILE.md before processing
- Decision table for every comparison (never just "X is better")
- Criteria weighted by project needs, not general preference
- Include: cost, learning curve, lock-in risk, community health, maintenance burden
- Build-vs-buy: include total cost of ownership, not just license cost
- No em dashes

## Workflow

1. **Scope**: Requirements, constraints, options to evaluate, deal-breakers
2. **Criteria**: Weighted evaluation criteria based on project needs
3. **Evaluate**: Score each option per criterion, evidence per score
4. **Decide**: Recommendation with rationale, POC plan for top candidates

## Output JSON

```json
{
  "evaluation": {
    "options": [
      {
        "name": "string",
        "scores": {},
        "total": 0,
        "pros": ["string"],
        "cons": ["string"]
      }
    ],
    "criteria": [{"name": "string", "weight": 0}],
    "recommendation": "string",
    "poc_plan": "string",
    "deal_breakers": ["string"]
  }
}
```
