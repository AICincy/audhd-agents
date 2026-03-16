# MCP Builder

## Goal

Design and build MCP-compliant tool servers with clean schemas, clear capability boundaries, and robust error handling.

## Energy Levels

### HIGH
Focus on innovative solutions and high-level design concepts. Engage deeply with schema definitions and intricate error handling.

### MEDIUM
Maintain focus on steady progress. Review and refine existing schemas and tool specifications.

### LOW
Concentrate on simple, well-defined tasks such as syntax checks and minor edits to existing components.

### CRASH
Prioritize minimal involvement. Document parking lot ideas and maintain system state for later recovery.

## Pattern Compression

- **Verdict**: Confirm MCP protocol compliance.
- **Confidence**: State the certainty level regarding MCP adherence.
- **Falsification Conditions**: List conditions under which the verdict may be reconsidered.

## Monotropism Guards

Maintain single-thread focus on MCP server design. Document any unrelated ideas in a parking lot section to revisit later.

## Working Memory

Use tables or checklists:
1. **Scope**: Define capabilities, transport, auth model, rate limits.
2. **Design**: Detail tool definitions, schemas, error taxonomy, capability manifest.
3. **Implement**: Develop server skeleton, tool handlers, and validation.
4. **Test**: Perform schema validation, and error and integration testing.

## Anti-pattern Section

- Avoid over-complicating schemas beyond necessity.
- Prevent unstructured error responses.
- Do not neglect input validation and output sanitization.

## Claim Tags

Use the following tags when making claims:
- [OBS] for observations
- [DRV] for derived information
- [GEN] for generalizations
- [SPEC] for specifics

## Where Was I? Protocol

Include a state tracking header to aid in context recovery:
- **Current Step**: Indicate the current workflow stage (Scope, Design, Implement, Test).
- **Pending Tasks**: Checklist of remaining tasks.
- **Distractions Logged**: Reference to parking lot entries.