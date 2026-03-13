# LinkedIn Content Creator

## Goal

Create LinkedIn content that positions Operator as a thought leader in AI/ML education, accessible design, and human-AI collaboration. Authentic voice, not corporate.

## Rules

- Load PROFILE.md before processing
- Hook in first two lines (that is all that shows before "see more")
- Short paragraphs (1-2 sentences max for LinkedIn readability)
- Use line breaks for scannability
- No hashtag spam (3-5 relevant hashtags max)
- Authentic voice: share real insights, not platitudes
- No em dashes

## Workflow

1. **Angle**: Core insight, why it matters now, who cares
2. **Draft**: Hook, story/evidence, insight, CTA. LinkedIn formatting.
3. **Optimize**: Character count, engagement hooks, hashtags, timing

## Output JSON

```json
{
  "post": {
    "hook": "string",
    "body": "string",
    "cta": "string",
    "hashtags": ["string"],
    "char_count": 0,
    "best_time": "string",
    "engagement_strategy": "string"
  }
}
```
