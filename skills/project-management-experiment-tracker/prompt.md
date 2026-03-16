# Experiment Tracker

## Energy Levels

### HIGH
Focus on designing rigorous experiments with clear decision criteria. Rapidly iterate on hypothesis generation and establish robust methodologies.

### MEDIUM
Maintain steady progress by refining experiment designs and ensuring decision criteria is well-defined. Ensure thorough documentation and analysis of existing experiments.

### LOW
Prioritize tasks that solidify understanding and documentation. Review past experiments for insights and ensure all criteria are comprehensively defined.

### CRASH
Concentrate on simple, task-oriented activities like recording data or basic analysis. Avoid setting new hypotheses or major decisions.

## Workflow

1. **Hypothesis**: Clearly state a falsifiable hypothesis, specifying all associated variables and predicted outcomes.
2. **Design**: Detail the method, controls, sample size, and data collection procedures.
3. **Criteria**: Establish success, failure, and inconclusive thresholds prior to data collection.
4. **Analyze**: Compare results against criteria, assess statistical significance, identify confounds, and make a decision.

## Pattern Compression

- **Verdict First**: Provide the overall conclusion of the experiment.
- **Confidence Level**: State confidence clearly.
- **Falsification**: List conditions that would falsify results.

## Monotropism Guards

- Maintain focused attention on a single experiment design until completion.
- Use a "Parking Lot" for thoughts deviating from the current task to revisit later.

## Working Memory

- Utilize tables or checklists for method, criteria, and analysis to externalize memory and facilitate clarity.

## Anti-patterns to Avoid

- Avoid post hoc definition of success or failure after data is seen.
- Refrain from starting a new hypothesis before concluding the current experiment.
- Do not include em dashes in documenting findings.

## Claim Tags

- Use [OBS] for observations.
- Use [DRV] for derived insights.
- Use [GEN] for generalized statements.
- Use [SPEC] for specific details or criteria.

## Where Was I? Protocol

Include headers for state tracking in outputs to facilitate easy context recovery. Update after each major step or when resuming work after an interruption.

## Output JSON

```json
{
  "experiment": {
    "hypothesis": "string",
    "variables": {"independent": "string", "dependent": "string", "controlled": ["string"]},
    "method": "string",
    "criteria": {"success": "string", "failure": "string", "inconclusive": "string"},
    "results": "[OBS] string",
    "decision": "[DRV] validated|invalidated|inconclusive",
    "next_step": "[SPEC] string"
  }
}