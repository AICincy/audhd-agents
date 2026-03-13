# Executive Summary Generator

## Goal

Compress complex inputs into decision-ready executive summaries. Conclusion first. One decision per summary. Numbers, not adjectives.

## Rules

- Load KRASS.md before processing
- 325-475 words target, 500 max. Density over length.
- Lead with recommendation or key insight (never bury the lead)
- Every finding includes at least one quantified or comparative data point
- Recommendations must be specific and actionable, not "explore further"
- Bold strategic implications
- Tag data sources: [OBS] for sourced data, [SPEC] for projections
- No em dashes

## Workflow

1. **Scope**: Audience (who, priorities, context level), decision (what they need to decide), sources (documents to synthesize), framework (SCQA/Pyramid), tone (direct, evidence-backed)
2. **Analyze**: Extract key findings, identify single most important insight, organize evidence hierarchically (Pyramid: conclusion first), quantify every claim
3. **Draft**: SCQA structure (Situation, Complication, Question, Answer), each paragraph serves one purpose, bold strategic implications
4. **Validate**: Word count (325-475, 500 max), every finding quantified, recommendation actionable and specific, no jargon without audience-confirmed expertise

## Output JSON

```json
{
  "summary": {
    "title": "string",
    "audience": "string",
    "decision": "string",
    "framework": "SCQA|Pyramid|custom",
    "word_count": "number",
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
