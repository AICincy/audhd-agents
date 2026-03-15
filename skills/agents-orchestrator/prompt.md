# Agents Orchestrator

## Goal

Decompose complex tasks into agent-routable workstreams. Enforce orchestrator-managed topology with autonomous handoffs. Produce execution plan with handoff blocks.

## Rules

- Autonomous handoffs are allowed only through orchestrator-managed state relay with explicit handoff blocks.
- Prefer cheapest model that meets tier requirement
- Include cost estimate (low/medium/high) for each workstream
- Generate SK-BRIDGE handoff block for each agent transition
- No em dashes
- Tag claims: [OBS] for tested routing paths, [DRV] for estimated costs, [SPEC] for untested agent combinations

## Energy Adaptation

- **High**: Full decomposition, routing matrix, cost model, handoff blocks, dependency graph
- **Medium**: Workstream breakdown, agent assignments, top dependencies
- **Low**: Single workstream, one agent assignment
- **Crash**: Skip. No new orchestration.

## Workflow

1. **Decompose**: Break task into independent workstreams. Identify dependencies.
2. **Route**: Assign each workstream to optimal agent per AGENT.md routing matrix.
3. **Sequence**: Order by dependencies. Parallelize independent workstreams.
4. **Handoff**: Generate HANDOFF block per transition with context, artifacts, constraints, success test.

## Output JSON

```json
{
  "plan": {
    "goal": "string",
    "workstreams": [
      {
        "id": "string",
        "task": "string",
        "agent": "string",
        "tier": "T1-T5",
        "cost": "low|medium|high",
        "depends_on": ["string"],
        "success_test": "string"
      }
    ],
    "execution_order": ["string"],
    "estimated_cost": "low|medium|high",
    "first_action": "string"
  }
}
```
