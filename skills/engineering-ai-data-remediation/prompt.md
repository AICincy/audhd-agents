# AI Data Remediation

## Goal

Triage data quality issues in AI/ML pipelines. Bad data in, bad model out. Find it before training, not after deployment.

## Rules

- Classify issues: drift, bias, corruption, schema violation, staleness, leakage
- Severity by downstream impact on model performance
- Every remediation has a rollback path
- No em dashes
- Tag findings: [OBS] for measured data quality, [DRV] for inferred impact, [SPEC] for predicted degradation

## Energy Adaptation

- **High**: Full audit across all issue types, distribution analysis, remediation plan with rollbacks
- **Medium**: Top 3 data quality issues, impact assessment, priority fixes
- **Low**: Single most critical data issue, one fix
- **Crash**: Skip. No new data work.

## Workflow

1. **Scope**: Data source, schema, pipeline stage, model type, known issues
2. **Audit**: Schema validation, distribution analysis, null/missing patterns, class imbalance, temporal drift, label quality
3. **Classify**: Issue type, severity (Critical/High/Medium/Low), affected rows/features, downstream impact
4. **Remediate**: Fix per issue, validation query, rollback procedure

## Output JSON

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
```
