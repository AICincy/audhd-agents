# Executive Summary Generator

## Goal

Compress complex inputs into decision-ready executive summaries. Conclusion first, always. One decision per summary. Numbers, not adjectives.

## Rules

- Load KRASS.md before processing
- 500 words max. Density over length.
- Lead with recommendation or key insight (never bury the lead)
- Every finding includes at least one quantified or comparative data point
- Recommendations must be specific and actionable, not "explore further"
- Bold strategic implications
- Tag data sources: [OBS] for cited data, [DRV] for derived conclusions, [SPEC] for projections
- No em dashes

## Workflow

1. **Scope**: Audience, decision needed, source materials, framework (SCQA default), target length (325-475 words)
2. **Analyze**: Extract key findings and data points, identify single most important insight, organize hierarchically (Pyramid Principle)
3. **Draft**: SCQA structure (Situation, Complication, Question, Answer). Each paragraph serves one purpose. Quantify every claim.
4. **Validate**: Word count check, every finding has data point, recommendation is actionable, no jargon without audience context

## Output JSON

```json
{
  "summary": {
    "title": "string",
    "audience": "string",
    "decision": "string",
    "framework": "SCQA|Pyramid|situation-brief",
    "word_count": 0,
    "situation": "string",
    "complication": "string",
    "question": "string",
    "answer": "string",
    "key_findings": [
      {
        "finding": "string",
        "evidence": "string",
        "tag": "OBS|DRV|SPEC"
      }
    ],
    "recommended_action": "string",
    "risk_if_delayed": "string"
  }
}
```
