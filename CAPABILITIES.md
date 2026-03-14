# Capability Map

Maps all 51 skills to 10 atomic capabilities. Each skill has one primary capability and zero or one secondary.

## Capabilities

| Capability | Description | Primary Skills | Count |
| --- | --- | --- | --- |
| research | Gather and trace information | ux-researcher, trend-researcher, evidence-collector | 3 |
| analyze | Find patterns, risks, anomalies | code-reviewer, incident-response, nudge-engine, test-results-analyzer | 4 |
| synthesize | Merge inputs into unified output | feedback-synthesizer, analytics-reporter, exec-summary-generator | 3 |
| generate | Produce new artifacts | rapid-prototyper, frontend-dev, devops, git-workflow, ai-engineer, technical-writer, training, image-prompt, inclusive-visuals, ui-designer, visual-storyteller, content-creator, linkedin-creator, dev-advocate, doc-generator, mcp-builder | 16 |
| transform | Convert formats and structures | ai-data-remediation, data-engineer, lsp-index-engineer | 3 |
| evaluate | Assess quality and performance | api-tester, perf-benchmarker, reality-checker, tool-evaluator, model-qa, experiment-tracker, brand-guardian | 7 |
| plan | Create architectures and roadmaps | software-architect, backend-architect, sprint-prioritizer, project-shepherd, project-manager, ux-architect | 6 |
| orchestrate | Coordinate skills and agents | agents-orchestrator | 1 |
| audit | Check compliance and security | compliance-auditor, automation-governance, security-engineer, accessibility-auditor, legal-compliance-checker | 5 |
| optimize | Improve performance and efficiency | autonomous-optimization, database-optimizer, workflow-optimizer | 3 |

**Total: 51 skills across 10 capabilities** (some skills appear as secondary in other capabilities)

## Capability Graph Chains

| Chain | Sequence | Use Case |
| --- | --- | --- |
| research_to_report | research > analyze > synthesize | Investigation and reporting |
| build_and_validate | plan > generate > evaluate > optimize | Full build cycle |
| code_review_pipeline | analyze > audit > evaluate | Code quality checks |
| content_pipeline | research > plan > generate > evaluate | Content creation |
| security_pipeline | audit > analyze > generate | Vulnerability remediation |
| feedback_loop | research > synthesize > analyze > plan | User feedback processing |

## Implementation Status

| Milestone | Status | Notes |
| --- | --- | --- |
| Capability definitions | Done | 10 capabilities defined in `capabilities/` |
| Graph and routing rules | Done | `graphs/capability_graph.yaml`, `graphs/routing_rules.yaml` |
| Skill mapping (51 skills) | Done | All skills have `skill.yaml`, `prompt.md`, `schema.json`, `examples.json` |
| API validation | Not started | Validate skills with real API calls |
| Runtime planner | Not started | Build planner/executor in `runtime/` |
| Capability-aware routing | Not started | Migrate `adapters/router.py` to use capability graph |
| Skill-level capability tags | Not started | Add `capabilities:` field to each `skill.yaml` |
