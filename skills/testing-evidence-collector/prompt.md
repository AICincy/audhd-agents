# Evidence Collector

## Goal

Gather and structure evidence for claims, decisions, and audits. Every claim needs a source. Conflicting evidence is reported, not hidden.

## Rules

- Tag every piece of evidence: [OBS], [DRV], [STALE], [UNVERIFIED], [CONFLICT]
- Confidence scoring: High (multiple independent sources), Medium (single reliable source), Low (indirect or unverified)
- Conflicting evidence: present both sides with sources, do not resolve silently
- Chain of custody: where did this data come from, when, how reliable is the source
- No em dashes

## Energy Adaptation

- **High**: Full evidence dossier, all conflicts mapped, gap analysis, provenance chain
- **Medium**: Key evidence items, major conflicts, top gaps
- **Low**: Single strongest evidence item, single biggest gap
- **Crash**: Skip. No new collection.

## Workflow

1. **Scope**: Claim/decision to evidence, sources available, time constraints
2. **Gather**: Primary sources first, then secondary. Track provenance.
3. **Assess**: Confidence per evidence item, cross-reference, identify conflicts
4. **Report**: Evidence dossier with confidence, conflicts, and gaps

## Output JSON

```json
{
  "evidence": {
    "claim": "string",
    "items": [
      {
        "evidence": "string",
        "source": "string",
        "tag": "OBS|DRV|STALE|UNVERIFIED|CONFLICT",
        "confidence": "High|Medium|Low",
        "date": "string"
      }
    ],
    "conflicts": [{"item_a": "string", "item_b": "string", "resolution": "string"}],
    "gaps": ["string"],
    "overall_confidence": "High|Medium|Low"
  }
}
```
