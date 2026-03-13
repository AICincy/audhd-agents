# Document Generator

## Goal

Generate professional documents from structured inputs. Consistent formatting, accessible output, appropriate formality for context.

## Rules

- Load PROFILE.md before processing
- Match formality to document type (proposal is formal, internal memo is direct)
- All documents have: purpose statement, audience, date, version
- Tables for structured data, not prose
- Accessible formatting: headings hierarchy, alt text, readable fonts
- No em dashes

## Workflow

1. **Scope**: Document type, audience, purpose, source data, template
2. **Structure**: Outline, section purposes, data placement
3. **Generate**: Content per section, formatting, data tables
4. **Validate**: Completeness, accuracy, formatting, accessibility

## Output JSON

```json
{
  "document": {
    "title": "string",
    "type": "string",
    "audience": "string",
    "purpose": "string",
    "sections": [
      {
        "heading": "string",
        "content": "string"
      }
    ],
    "metadata": {"date": "string", "version": "string", "author": "string"}
  }
}
```
