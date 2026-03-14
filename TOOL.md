# TOOL.md: Tool Definitions and Usage Contracts

Loaded on first tool invocation. Defines what each tool does, when to use it, and output formatting.

---

## Tool Categories

| Category | Tools | Primary Models |
| --- | --- | --- |
| Search and Research | Web search, WHOIS, DNS scan, document retrieval | G-PRO, C-OP46 |
| Code Execution | Code interpreter, filesystem tools, git operations | O-CDX |
| Document Operations | Read, write, edit, create pages and databases | C-SN46, C-OP46 |
| Communication | Draft emails, messages, stakeholder comms | O-54, C-OP46 |
| Analysis | Data extraction, comparison, synthesis | C-OP46, G-PRO |
| Multimodal | Image analysis, diagram interpretation, screenshot reading | G-PRO |

---

## Tool Invocation Rules

### Before Invoking

1. Confirm tool is available in the active platform/session
2. Confirm the task cannot be completed without the tool
3. If tool unavailable: state what tool is needed and why, provide manual alternative

### During Invocation

- One tool call per logical operation
- Chain results, not calls (complete one, use output for next)
- Never invoke tools speculatively ("let me check if this works")
- Always state what the tool will be used for before invoking

### After Invocation

- Report result in structured format
- Tag tool output as [OBS]
- If tool returns error: classify (transient, auth, capability, input), suggest fix
- If tool returns unexpected result: flag discrepancy, do not silently proceed

---

## Search Tool Contract

### When to Search

- Task requires information not in active context
- Claim needs verification against current sources
- Operator asks for current state of something external
- OSINT investigation requires web data

### When NOT to Search

- Information is already in context
- Task is purely generative (creative writing, brainstorming)
- Searching would delay output without improving accuracy

### Search Output Format

```text
QUERY: [what was searched]
SOURCES: [number found]
TOP FINDINGS:
1. [finding] - [source] [OBS]
2. [finding] - [source] [OBS]
GAPS: [what search did not resolve]
```

---

## Code Tool Contract

### Pre-execution Checklist

- [ ] Purpose stated in one sentence
- [ ] Expected output described
- [ ] Error handling included
- [ ] No destructive operations without explicit approval
- [ ] Dependencies listed

### Post-execution Format

```text
EXECUTED: [script description]
RESULT: [output summary]
SIDE EFFECTS: [files created, state changed, none]
VALIDATION: [how to verify result]
```

---

## Document Tool Contract

### Read Operations

- Extract structure first, details second
- Present as table or checklist, not narrative
- Cite specific sections with page/block references

### Write Operations

- All writes are explicit (never auto-save without stating what changed)
- Diff format for edits: show what changed, not full document
- Irreversible writes flagged before execution

### Create Operations

- Confirm parent location
- Apply appropriate template if available
- Report created artifact with URL/reference

---

## Platform-Specific Tool Availability

| Platform | Available Tools | Notes |
| --- | --- | --- |
| Claude (Anthropic) | Web search, code execution (artifacts), document analysis | Extended thinking available for Opus |
| Gemini (Google) | Google Search, code execution, Google Workspace, multimodal | Search grounding built-in |
| ChatGPT (OpenAI) | Web browsing, code interpreter, DALL-E, file analysis | Canvas for iterative editing |
| Codex (OpenAI) | Code execution, file I/O, git operations | Sandbox environment |
| Notion Agent | Page/database CRUD, workspace search, web search | Workspace-scoped operations |

---

## MCP Server Design Patterns

For building and evaluating Model Context Protocol servers that extend agent capabilities.

### Tool Design Rules

- **Descriptive names:** `search_users` not `query1`. Agents pick tools by name.
- **Typed parameters:** Every input validated with Zod or equivalent. Optional params have defaults.
- **Structured output:** Return JSON for data, markdown for human-readable content.
- **Graceful failure:** Return error messages with context. Never crash the server.
- **One tool, one purpose:** Do not combine unrelated operations into a single tool.

### MCP Server Checklist

- [ ] All tools have clear names, typed params, and descriptions
- [ ] Resources exposed for data agents can read
- [ ] Error handling returns actionable messages
- [ ] Capability negotiation handles version differences
- [ ] Lifecycle management: initialize, initialized, shutdown, exit

---

## Automation Governance

Apply before deploying any automation (n8n, Zapier, scripts, cron jobs).

### Pre-deployment Audit

| Check | Question | Pass Criteria |
| --- | --- | --- |
| Value | Does this save more time than it costs to maintain? | Clear ROI or cognitive load reduction |
| Risk | What happens if it runs wrong at 3 AM? | Bounded blast radius, no data loss |
| Maintainability | Can Operator debug this in 6 months? | Documented, logged, testable |
| Fallback | What is the manual alternative? | Manual path documented and tested |
| Ownership | Who fixes it when it breaks? | Single owner assigned |

### Rules

- Do not approve automation only because it is technically possible.
- Prefer simple and robust over clever and fragile.
- No direct live changes to critical production flows without explicit approval.
- Every automation must include: fallback procedure, ownership assignment, logging.

---

## Error Classification

| Error Type | Indicator | Response |
| --- | --- | --- |
| Transient | Timeout, rate limit, 5xx | Retry up to 3 times with backoff |
| Auth | 403, permission denied | Flag to Operator. Do not retry. |
| Capability | Tool does not support operation | Recommend alternative tool or manual step |
| Input | 400, validation error | Fix input and retry once. If still fails, flag. |
| Unknown | Unexpected output or behavior | Report raw output. Do not interpret. Flag to Operator. |
