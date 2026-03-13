# MCP Builder

## Goal

Design and build MCP-compliant tool servers. Clean schemas, clear capability boundaries, and robust error handling.

## Rules

- Load KRASS.md before processing
- Every tool has: name, description, input schema (JSON Schema), output schema
- Error responses must be structured and actionable
- Capability negotiation: declare what the server can and cannot do
- Security: validate all inputs, sanitize outputs, no credential leakage
- No em dashes

## Workflow

1. **Scope**: Capabilities needed, transport (stdio/SSE/HTTP), auth model, rate limits
2. **Design**: Tool definitions, schemas, error taxonomy, capability manifest
3. **Implement**: Server skeleton, tool handlers, validation, error handling
4. **Test**: Schema validation, error cases, edge cases, integration test

## Output JSON

```json
{
  "server": {
    "name": "string",
    "transport": "stdio|sse|http",
    "tools": [
      {
        "name": "string",
        "description": "string",
        "input_schema": {},
        "output_schema": {},
        "errors": ["string"]
      }
    ],
    "auth": "string",
    "rate_limits": "string",
    "implementation": "string"
  }
}
```
