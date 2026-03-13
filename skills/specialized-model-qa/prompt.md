# Model QA

## Goal

Systematically evaluate LLM outputs. Vibes are not a test suite. Define criteria, measure consistently, compare across models.

## Rules

- Load KRASS.md before processing
- Evaluation criteria defined before testing (not after seeing outputs)
- Score on multiple dimensions: accuracy, completeness, format compliance, safety
- Cross-model comparison uses identical prompts and evaluation rubric
- Track regressions across model versions
- No em dashes

## Workflow

1. **Scope**: What to evaluate, criteria, models to compare, baseline
2. **Design**: Test cases, evaluation rubric, scoring method
3. **Execute**: Run prompts, collect outputs, apply rubric
4. **Report**: Scores by criterion and model, regressions, recommendations

## Output JSON

```json
{
  "evaluation": {
    "test_cases": 0,
    "models_tested": ["string"],
    "criteria": ["string"],
    "results": [
      {
        "model": "string",
        "scores": {},
        "overall": 0,
        "regressions": ["string"]
      }
    ],
    "winner": "string",
    "recommendation": "string"
  }
}
```
