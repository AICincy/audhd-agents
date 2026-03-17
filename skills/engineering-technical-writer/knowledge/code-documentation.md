---
title: Code Documentation Patterns
domain: technical-writing
subdomain: code-level
audience: developers, code reviewers, technical writers
tags: [docstrings, comments, inline, readme, changelog, type-hints]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Code Documentation Patterns

## Purpose

Provide reusable patterns for code-level documentation: docstrings, inline comments, README files, changelogs, and type annotations. Code documentation explains the "why"; the code itself explains the "what". [general]

## Documentation Layers

| Layer | Scope | Purpose | Owner |
| --- | --- | --- | --- |
| Type annotations | Function signatures | Machine-readable contracts | Developer |
| Docstrings | Functions, classes, modules | API contract for callers | Developer |
| Inline comments | Code blocks | Explain non-obvious decisions | Developer |
| README | Repository/package | Orientation and quickstart | Maintainer |
| CHANGELOG | Release | What changed and why | Maintainer |
| CONTRIBUTING | Repository | How to contribute | Maintainer |

## Docstring Patterns

### Python (Google Style)

```python
def resolve_schema(schema: dict, skill_dir: Path) -> dict:
    """Resolve allOf/$ref in a skill schema to a flat schema.

    Merges properties and required fields from referenced schemas
    into a single top-level dict for builder consumption.

    Args:
        schema: Raw JSON schema, possibly containing allOf/$ref.
        skill_dir: Directory containing the skill for relative
            $ref resolution.

    Returns:
        Flattened schema dict with merged properties and required
        at top level.

    Raises:
        FileNotFoundError: If a $ref target file does not exist.

    Example:
        >>> schema = {"allOf": [{"$ref": "../_base/schema_base.json"}]}
        >>> resolved = resolve_schema(schema, Path("skills/my-skill"))
        >>> "properties" in resolved
        True
    """
```

### Python (NumPy Style)

```python
def validate_output(output_text, active_mode="execute", energy_level="medium"):
    """Validate model output against cognitive contracts.

    Parameters
    ----------
    output_text : str
        The raw output text to validate.
    active_mode : str, optional
        Current operating mode (default: "execute").
    energy_level : str, optional
        Operator energy level (default: "medium").

    Returns
    -------
    ValidationResult
        Dataclass with passed, violations, and warnings fields.
    """
```

### TypeScript (TSDoc)

```typescript
/**
 * Resolves a skill schema by merging allOf references.
 *
 * @param schema - Raw JSON schema with potential $ref entries
 * @param skillDir - Path to the skill directory for relative resolution
 * @returns Flattened schema with top-level properties
 * @throws {SchemaError} When a referenced file cannot be loaded
 *
 * @example
 * ```ts
 * const resolved = resolveSchema(rawSchema, "./skills/writer");
 * console.log(resolved.properties);
 * ```
 */
```

### Docstring Rules

1. First line: imperative verb + what the function does, under 80 characters. [general]
2. Document all parameters with types, defaults, and constraints. [general]
3. Document return type and structure. [general]
4. Document raised exceptions with conditions. [general]
5. Include a code example for non-trivial functions. [observed]
6. Do not repeat the function signature in prose. [general]
7. Keep docstrings updated when the function changes. [observed]

## Inline Comment Rules

### When to Comment

| Situation | Comment? | Example |
| --- | --- | --- |
| Non-obvious algorithm | Yes | "Binary search on sorted timestamps" |
| Business rule | Yes | "Discount applies only to annual plans" |
| Workaround for known issue | Yes | "Workaround for upstream bug #1234" |
| Performance optimization | Yes | "Pre-allocate to avoid repeated resizing" |
| Obvious operation | No | `i += 1  # increment i` is noise |
| Type-annotated parameter | No | Type hints replace type comments |

### Comment Style

```python
# Correct: explains WHY
# NFKC normalization collapses unicode confusables before injection detection.
text = unicodedata.normalize("NFKC", text)

# Wrong: restates WHAT the code does
# Normalize the text using NFKC
text = unicodedata.normalize("NFKC", text)
```

### TODO/FIXME/HACK Tags

```python
# TODO(author): Brief description of planned work. Ticket: PROJ-123
# FIXME(author): Bug description. Reproducer: [steps]. Ticket: PROJ-456
# HACK(author): Why this workaround exists. Remove when: [condition]
```

Rules for tags: [general]
- Always include the author or team responsible.
- Always link a ticket or issue number.
- State the condition under which the tag can be removed.

## README Structure

### Repository README Template

```markdown
# Project Name

One-line description of what this project does.

## Quickstart

Three commands or fewer to get running:

    git clone <repo>
    pip install -e .
    python -m myproject

## Usage

Minimal working example with expected output.

## Architecture

Brief description with link to detailed architecture docs.

## Contributing

Link to CONTRIBUTING.md.

## License

SPDX identifier and link.
```

### README Rules

1. Quickstart must work on a fresh clone. Test it. [observed]
2. Include prerequisites (language version, OS, dependencies). [general]
3. Show expected output for code examples. [general]
4. Link to detailed docs; do not duplicate them in the README. [general]
5. Keep the README under 300 lines. [general]

## CHANGELOG Patterns

### Keep a Changelog Format

```markdown
# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.2.0] - 2026-03-17

### Added
- Knowledge base documents for RAG retrieval
- Export script for zip packaging

### Changed
- Technical writer skill now references knowledge base

### Fixed
- Schema validation for nested allOf references

### Removed
- Deprecated v0 API endpoints
```

### Changelog Rules

1. Group changes under Added, Changed, Deprecated, Removed, Fixed, Security. [general]
2. Write entries for humans, not machines: "Added user search by email" not "Added endpoint". [general]
3. Link version headers to git tags or release pages. [general]
4. Unreleased section at top for in-progress changes. [general]

## Type Annotation Patterns

### Python Type Hints

```python
from __future__ import annotations
from pathlib import Path

def load_skill(skill_dir: Path) -> dict[str, Any]:
    """Load canonical skill files from a skill directory."""
    ...

def validate_output(
    output_text: str,
    active_mode: str = "execute",
    energy_level: str = "medium",
    task_tier: str = "T3",
) -> ValidationResult:
    ...
```

Rules: [general]
- Use `from __future__ import annotations` for forward reference support.
- Annotate all public function signatures.
- Use `TypeAlias` for complex repeated types.
- Prefer `dict[str, Any]` over `Dict[str, Any]` (Python 3.9+).

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| Commented-out code | Version control handles history | Delete it; recover from git |
| Docstring that restates the name | `def get_user` with docstring "Gets user" adds nothing | Describe behavior, edge cases, constraints |
| Stale comments | Misleading comments are worse than none | Update comments when code changes |
| No README quickstart | New developers cannot start | Add working quickstart section |
| CHANGELOG as git log dump | Noise; unreadable | Curate meaningful entries per release |

## Grounding Checklist

Before publishing code documentation, verify: [observed]
- [ ] All public functions have docstrings with Args, Returns, Raises
- [ ] Inline comments explain "why", not "what"
- [ ] README quickstart works on a fresh clone
- [ ] CHANGELOG follows Keep a Changelog format
- [ ] Type annotations exist on all public interfaces
- [ ] TODO/FIXME tags have author, ticket, and removal condition
- [ ] No commented-out code remains in the codebase
