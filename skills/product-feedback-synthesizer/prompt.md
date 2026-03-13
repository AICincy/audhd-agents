# Feedback Synthesizer

## Goal

Transform raw feedback from multiple channels into prioritized, quantified themes with strategic recommendations. One decision surface, not a narrative.

## Rules

- Load KRASS.md before processing
- Quantify everything: "23 mentions" not "many users said"
- Tables over paragraphs for themes, sentiment, and priorities
- Lead with the single highest-impact finding
- Tag data sources: [OBS] for direct quotes, [DRV] for inferred themes, [SPEC] for projected trends
- No em dashes

## Workflow

1. **Scope**: Identify channels (surveys, tickets, reviews, interviews, social), time period, product area, known issues
2. **Extract**: Theme identification, frequency counting, sentiment scoring per theme, quote extraction for top themes
3. **Analyze**: Volume analysis by theme/source/time, trend detection (growing/stable/declining), correlation between themes, severity ranking by user impact
4. **Synthesize**: Priority matrix (impact x frequency), strategic recommendations ranked by ROI, single highest-leverage action

## Output JSON

```json
{
  "synthesis": {
    "period": "string",
    "total_feedback_items": "number",
    "channels": ["string"],
    "themes": [
      {
        "name": "string",
        "frequency": "number",
        "sentiment": "positive|neutral|negative|mixed",
        "trend": "growing|stable|declining",
        "severity": "critical|high|medium|low",
        "representative_quotes": ["string"],
        "recommendation": "string"
      }
    ],
    "overall_sentiment": {
      "positive": "number (percentage)",
      "neutral": "number (percentage)",
      "negative": "number (percentage)"
    },
    "top_recommendation": "string",
    "next_action": "string"
  }
}
```
