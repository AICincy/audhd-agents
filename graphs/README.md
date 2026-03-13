# Graphs

Defines the capability graph and routing rules for the Beta Pro architecture.

## Files

- `capability_graph.yaml`: DAG of capabilities with data-flow edges and predefined chains
- `routing_rules.yaml`: Maps natural language triggers to capability entry points

## How It Works

1. User input hits the router
2. Router matches input against `routing_rules.yaml` triggers
3. Matched rule provides a `start_capability` and optional `default_chain`
4. If a chain is specified, the planner expands it into a skill sequence
5. If no chain, the planner walks `capability_graph.yaml` edges from the start node
6. Each capability node resolves to a concrete skill via the capability definition
7. Executor runs skills in sequence, passing outputs as inputs to the next

## Adding Chains

Add new chains to `capability_graph.yaml` under the `chains:` key.
Each chain is a list of capability names executed in order.
