# Capability Map

Maps all 47 skills to 10 atomic capabilities. Each skill has one primary capability and zero or one secondary.

## Capabilities

| Capability | Description | Primary Skills | Count |
| --- | --- | --- | --- |
| research | Gather and trace information | ux-researcher, trend-researcher, evidence-collector, github-pr-lister | 4 |
| analyze | Find patterns, risks, anomalies | code-reviewer, incident-response, nudge-engine, test-results-analyzer | 4 |
| synthesize | Merge inputs into unified output | feedback-synthesizer, analytics-reporter | 2 |
| generate | Produce new artifacts | rapid-prototyper, frontend-dev, devops, git-workflow, ai-engineer, technical-writer, training, image-prompt, inclusive-visuals, ui-designer, visual-storyteller, content-creator, dev-advocate, doc-generator, mcp-builder | 15 |
| transform | Convert formats and structures | ai-data-remediation, data-engineer, lsp-index-engineer | 3 |
| evaluate | Assess quality and performance | api-tester, perf-benchmarker, reality-checker, tool-evaluator, model-qa, experiment-tracker, brand-guardian | 7 |
| plan | Create architectures and roadmaps | software-architect, sprint-prioritizer, project-shepherd, project-manager, ux-architect | 5 |
| orchestrate | Coordinate skills and agents | agents-orchestrator | 1 |
| audit | Check compliance and security | compliance-auditor, automation-governance, security-engineer, accessibility-auditor | 4 |
| optimize | Improve performance and efficiency | autonomous-optimization, database-optimizer | 2 |

**Total: 47 skills across 10 capabilities** (some skills appear as secondary in other capabilities)

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
| Skill mapping (47 skills) | Done | All skills have `skill.yaml`, `prompt.md`, `schema.json`, `examples.json` |
| Skill-level capability tags | Done | All 47 `skill.yaml` files have `capabilities:` field |
| Runtime planner | Done | `runtime/planner.py` with trigger matching and chain resolution |
| Capability-aware routing | Done | `adapters/router.py` supports `execute_chain` for capability chains |
| API validation (live calls) | Partial | Config validation passes; full live skill validation in progress |
| Cognitive pipeline | Done | `runtime/cognitive.py`, `runtime/hooks.py`, `runtime/validation.py` |
| FastAPI runtime | Done | `runtime/app.py` with `/healthz`, `/readyz`, `/execute` |
| Provider adapters | Done | Google and OpenAI active (Anthropic removed) |
| CI pipeline | Done | `.github/workflows/python-package.yml` |
| CD pipeline | Done | `.github/workflows/deploy-cloud-run.yml` |

