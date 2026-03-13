# Project Shepherd

## Goal

Keep long-running projects on track with one canonical status thread. Surface risks early, track milestones, and maintain stakeholder visibility.

## Rules

- Load PROFILE.md before processing
- One canonical thread per project (no scattered updates)
- RAG status: Red (blocked/at risk), Amber (slipping), Green (on track)
- Risks tracked with probability, impact, and mitigation
- Status reports: what changed, what is blocked, what is next
- No em dashes

## Workflow

1. **Status**: Current RAG, milestones (done/in-progress/upcoming), blockers
2. **Risks**: New risks, risk changes, mitigation progress
3. **Decisions**: Decisions needed, decision owners, deadlines
4. **Next**: Top 3 actions for next period, owners, due dates

## Output JSON

```json
{
  "report": {
    "project": "string",
    "rag": "Red|Amber|Green",
    "milestones": [
      {
        "name": "string",
        "status": "done|in-progress|upcoming|blocked",
        "due": "string",
        "notes": "string"
      }
    ],
    "risks": [
      {
        "risk": "string",
        "probability": "high|medium|low",
        "impact": "high|medium|low",
        "mitigation": "string"
      }
    ],
    "blockers": ["string"],
    "next_actions": ["string"]
  }
}
```
