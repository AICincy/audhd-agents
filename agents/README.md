# Agent Compositions

This directory will contain agent composition definitions: pre-configured multi-skill workflows that chain capabilities for common tasks.

## Status

**Not yet implemented.** This is a planned feature.

## Planned Structure

Each agent composition will define:

- Which skills to invoke and in what order
- Data flow between skill invocations
- Success criteria and fallback behavior
- Energy-level constraints

## Examples (planned)

- `osint-investigator.yaml`: SA-NAME > SA-ADDR > SA-ORG > merge
- `code-review-pipeline.yaml`: code-reviewer > security-engineer > accessibility-auditor
- `content-pipeline.yaml`: trend-researcher > content-creator > brand-guardian

## Related

- `graphs/capability_graph.yaml`: Defines valid capability chains
- `graphs/routing_rules.yaml`: Routing constraints
- `AGENT.md`: Orchestration protocol and routing matrix
