---
description: Python conventions for audhd-agents.
---

# Code Style

- Python 3.11+
- Type hints on all signatures
- Pydantic v2 BaseModel
- FastAPI for HTTP
- pytest (mock adapters, no live API)
- `from __future__ import annotations`
- Docstrings on class/public function
- No star imports

## File naming
- Modules: `runtime/profile_loader.py`
- Classes: `CognitiveState`, `SkillRouter`
- Constants: `ENERGY_MODEL_POOLS`
- Tests: `tests/test_<module_name>.py`

## Import order
1. stdlib
2. third-party
3. local
