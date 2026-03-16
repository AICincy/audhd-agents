---
description: Reality checking. Prevents hallucinated claims.
---

# Reality Checker

Verify before claiming:
1. File exists: Run `ls` or `find`
2. Content matches: Read file
3. Tests pass: Run `pytest tests/ -v`
4. PR did what claimed: `git diff --stat`

## Claim tags
- [OBS] Directly read file/output
- [DRV] Derived from evidence
- [GEN] General knowledge
- [SPEC] Speculative

## Verification protocol
Run command. Read file. Check output.
