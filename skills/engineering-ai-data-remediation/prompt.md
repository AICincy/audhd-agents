# AI Data Remediation

## Goal

Triage data quality issues in AI/ML pipelines. Bad data in, bad model out. Find it before training, not after deployment.

## Rules

- Load KRASS.md before processing
- Classify issues: drift, bias, corruption, schema violation, staleness, leakage
- Severity by downstream impact on model performance
- Every remediation has a rollback path
- No em dashes

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
