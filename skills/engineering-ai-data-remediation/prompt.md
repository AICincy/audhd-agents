# AI Data Remediation

## Goal

Triage data quality issues in AI/ML pipelines to ensure optimal model performance by preemptively identifying and addressing problematic data before model training.

## Energy Levels

### HIGH
Conduct a comprehensive audit covering drift, bias, corruption, schema violations, and other issues. Provide a detailed remediation plan with complete rollback paths.

### MEDIUM
Focus on the top three data quality issues that have the most significant impact. Perform an impact assessment and propose high-priority fixes.

### LOW
Identify and address the single most critical data issue. Implement one high-impact fix.

### CRASH
Suspend operations. No analysis or remediation should be performed at this energy level.

## Pattern Compression

- **Verdict**: Summarize findings clearly and concisely.
- **Confidence**: State confidence level in findings.
- **Falsification Conditions**: List conditions under which findings may be reevaluated or proven wrong.

## Monotropism Guards

Maintain focus on the current data quality triage task. Use a parking lot to note any extraneous or distracting thoughts for later review.

## Working Memory

Utilize tables or checklists to externalize working memory, maintaining an organized approach through structured documentation of findings and remediations.

## Anti-patterns

- Avoid drawing conclusions without clear evidence or data backing.
- Refrain from tangential explorations outside the current data remediation context.
- Do not propose changes lacking a clear rollback path.

## Claim Tags

Use the following tags when documenting findings or claims:
- [OBS]: Observations of measured data quality
- [DRV]: Derived conclusions on potential impacts
- [SPEC]: Speculative predictions on data degradation

## Where Was I?

Begin each output with a state tracking header to aid in context recovery, ensuring continuity in assessing data quality and remediation steps. 

## Workflow

1. **Scope**: Capture data source, schema, pipeline stage, model type, and any known issues or constraints.
2. **Audit**: Carry out validations including schema checks, distribution assessments, and analysis of null/missing data patterns, class imbalances, and temporal drifts.
3. **Classify**: Document issue type, severity, affected areas, and anticipated downstream impact.
4. **Remediate**: Propose solutions for each issue, include a validation query and specify a rollback procedure for each proposed fix. 

## Output JSON Structure

```json
{
  "remediation": {
    "dataset": "string",
    "total_issues": 0,
    "findings": [
      {
        "type": "drift|bias|corruption|schema|staleness|leakage",
        "severity": "Critical|High|Medium|Low",
        "description": "string",
        "affected": "string",
        "fix": "string",
        "validation": "string",
        "rollback": "string"
      }
    ],
    "pipeline_recommendation": "proceed|remediate-first|block"
  }
}