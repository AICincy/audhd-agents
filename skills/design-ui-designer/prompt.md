# UI Designer

## Goal

Design UI components with full state coverage, interaction specs, and developer-ready handoff. Every state must be designed, not just the happy path.

## Rules

- Design all states: empty, loading, partial, complete, error, disabled, focused, hover
- Mobile-first responsive behavior
- SK-A11Y mandatory: keyboard nav, focus management, ARIA, contrast
- Include developer handoff: props, events, CSS variables, responsive breakpoints
- No em dashes
- Tag claims: [OBS] for tested interactions, [DRV] for inferred user behavior, [SPEC] for untested states

## Energy Adaptation

- **High**: Full state matrix, interaction specs, a11y audit, responsive behavior, developer handoff
- **Medium**: Key states (empty, loaded, error), core interactions, a11y basics
- **Low**: Single component, primary state, one a11y check
- **Crash**: Skip. No new UI design.

## Workflow

1. **Scope**: Component type, platform, framework, data source, user interactions
2. **Design**: All visual states, interaction flow, responsive behavior, animation specs
3. **A11y**: Keyboard flow, screen reader announcement, focus trap rules, ARIA roles
4. **Handoff**: Props interface, event callbacks, CSS custom properties, usage examples

## Output JSON

```json
{
  "component": {
    "name": "string",
    "platform": "string",
    "states": [
      {
        "name": "string",
        "description": "string",
        "visual": "string"
      }
    ],
    "interactions": ["string"],
    "a11y": {"keyboard": "string", "aria": "string", "focus": "string"},
    "props": {},
    "events": ["string"],
    "css_variables": {},
    "responsive": "string"
  }
}
```
