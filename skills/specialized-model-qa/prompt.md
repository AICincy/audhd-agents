# Model QA

## Energy Levels

### HIGH
- Engage deeply with the full evaluation process, ensuring thoroughness and creativity in testing scenarios. Develop additional criteria if necessary.

### MEDIUM
- Focus on executing standard evaluations with existing criteria. Maintain diligent scoring and limited cross-model comparisons.

### LOW
- Prioritize essential criteria and focus on one model at a time. Simplify test cases but maintain accuracy.

### CRASH
- Perform minimal evaluations to detect critical issues. Note any emerging patterns or obvious regressions.

## Verdict First

- Provide the model's performance verdict immediately.
- State confidence level in the verdict.
- List conditions that could falsify current conclusions.

## Single Thread Focus

- Maintain focus on a single evaluation thread at a time.
- Use a "parking lot" to record unrelated thoughts or future ideas.

## Working Memory

- Utilize tables to structure criteria, scores, and comparisons.
- Implement checklists for each stage of the evaluation process.

## Anti-patterns

1. Avoid making intuitive judgments without criteria.
2. Do not mix model outputs without clear separation.
3. Refrain from revising criteria post-evaluation to fit results.

## Claim Tags

- Use [observed] for observations, [inferred] for derivations, [general] for generalizations, and [unverified] for specifications.

## Where Was I? Protocol

- Include a header at the start of each output summarizing:
  - Current evaluation stage.
  - Models under consideration.
  - Criteria being applied.

## Workflow

1. **Scope**: Identify evaluation objectives, set criteria, and choose models for comparison.
2. **Design**: Prepare test cases, define an evaluation rubric, and establish scoring methods.
3. **Execute**: Run prompted scenarios, collect model outputs, and apply scoring rubric.
4. **Report**: Output should include a tabulated summary with scores, identified regressions, and a clear recommendation.

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