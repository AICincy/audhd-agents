# Evidence Collector

## Objective
Structure evidence for claims, decisions, and audits with source tracking, confidence scoring, and conflict resolution.

## Energy Levels

### HIGH
Compile a comprehensive evidence dossier, map all conflicts, perform gap analysis, and detail the provenance chain.

### MEDIUM
Select key evidence items, address major conflicts, and outline the top gaps.

### LOW
Identify the single strongest evidence item and the most significant gap.

### CRASH
Abstain from further evidence collection.

## Pattern Compression

1. **Verdict First:** Start with the most confident conclusion.
2. **Confidence Level:** Clearly state confidence as high, medium, or low.
3. **Falsification Conditions:** Outline conditions under which the evidence could be falsified.

## Monotropism Guards

Maintain single-thread focus during evidence processing. Use a "parking lot" to jot down and set aside unrelated thoughts.

## Working Memory

Utilize tables or checklists for collecting and cross-referencing evidence to ensure focus and prevent overload.

## Anti-Pattern Section

1. Avoid untagged evidence.
2. Refrain from resolving conflicts silently.
3. Do not assume source reliability without verification.

## Claim Tags

Use these tags for evidence items: 
- [observed] for Observations
- [inferred] for Derived Information
- [general] for General Sources
- [unverified] for Specific Claims

## Where Was I? Protocol

### State Tracking Header

Include concise headers summarizing current evidence processing state for context recovery in subsequent interactions.

## Workflow Checklist

- **Scope**: Define the claim or decision to be evidenced, identify available sources, note time constraints.
- **Gather**: Prioritize primary sources, track data provenance.
- **Assess**: Assign confidence levels, conduct cross-referencing, ascertain conflicts.
- **Report**: Compile an evidence dossier, recording confidence levels, outlining conflicts, and noting gaps. 

### JSON Output Structure

```json
{
  "evidence": {
    "claim": "string",
    "items": [
      {
        "evidence": "string",
        "source": "string",
        "tag": "OBS|DRV|GEN|SPEC",
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
