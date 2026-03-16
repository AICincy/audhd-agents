---
description: Enforces AuDHD cognitive architecture from PROFILE.md and AGENT.md.
---

# Cognitive Contract Enforcement

Code must implement cognitive architecture from PROFILE.md and AGENT.md.

## Skill prompt (prompt.md) must have:
1. Cognitive state branching (HIGH/MEDIUM/LOW/CRASH)
2. Pattern compression (verdict first, confidence, falsification)
3. Monotropism guards (one thread, parking lot)
4. Working memory externalization (tables, checklists)
5. Anti-pattern section
6. Claim tags ([OBS], [DRV], [GEN], [SPEC])
7. "Where Was I?" protocol

## Runtime code must handle:
1. CognitiveState parameter
2. Crash mode (no model call, save state)
3. Energy-adaptive model selection
4. Request tracing (request_id)

## Output validation:
- verdict field
- confidence in [0.0, 1.0]
- single_next_action
- parking_lot array
