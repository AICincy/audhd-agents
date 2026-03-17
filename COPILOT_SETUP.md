# COPILOT_SETUP.md: System Instructions for Skeletal Repository Scaffold

System instructions for GitHub Copilot (or any AI coding agent) to recreate the skeletal structure of this project. Grounded in verified reality: 184 tests passing, 47 skills building, syntax audit clean. Every claim below maps to existing, functional code.

---

## What This Project Actually Is

A multi-agent orchestration system designed around AuDHD cognitive patterns. Not a chatbot framework. Not a generic agent toolkit. Every design decision maps to one of five real cognitive patterns: monotropism (single-thread focus), pattern compression (verdict first), asymmetric working memory (maps over turn-by-turn), interest-based activation (micro-steps for low-interest tasks), executive function offload (infer and execute).

The system routes operator input through a cognitive-state-aware pipeline: input + cognitive_state goes to a router that reads energy/mode/tier, passes through hooks (21 total, 3 always-on), calls an LLM provider (OpenAI or Google), validates output against PROFILE.md contracts, and returns a response with cognitive_state echo.

---

## Step 1: Project Root and Configuration

Create these files first. They define the project identity and dependency surface.

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "audhd-agents"
version = "0.2.0"
description = "Multi-agent orchestration for AuDHD cognition"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "openai>=1.0",
    "google-genai>=1.67.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### .env.example

```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
GOOGLE_PROJECT_ID=...
GOOGLE_GENAI_USE_VERTEXAI=false
VERTEX_API_KEY=...
NOTION_WEBHOOK_SECRET=...
AUDHD_API_KEYS=key1,key2
APP_ENV=staging
REQUIRED_PROVIDERS=openai,google
LOG_LEVEL=INFO
```

### .gitignore

```
dist/
__pycache__/
*.pyc
.DS_Store
*.egg-info/
.env
node_modules/
*.log
venv/
.venv/
.claude/
*.code-workspace
.vscode/
```

### Dockerfile

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir . 2>/dev/null || true
COPY . .
RUN pip install --no-cache-dir .
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8080/healthz || exit 1
ENV PORT=8080
EXPOSE ${PORT}
CMD ["uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
```

---

## Step 2: Directory Structure

Create this exact tree. No extra directories. No placeholder READMEs unless noted.

```
audhd-agents/
├── adapters/           # LLM provider layer (OpenAI, Google)
│   ├── __init__.py
│   ├── base.py         # Abstract BaseAdapter with circuit breaker
│   ├── router.py       # SkillRouter: model resolution, failover, execution
│   ├── openai_adapter.py
│   ├── google_adapter.py
│   └── config.yaml     # Model registry (9 models, 2 providers)
├── agents/             # Agent compositions (9 domain agents)
│   └── {domain}-engineer/
│       ├── agent.yaml
│       ├── config.json
│       ├── examples.json
│       ├── prompt.md
│       ├── reality_adapter.json
│       ├── schema.json
│       ├── skills.json
│       └── tools.json
├── capabilities/       # 10 capability definitions
│   └── {name}.yaml     # analyze, audit, evaluate, generate, optimize,
│                        # orchestrate, plan, research, synthesize, transform
├── cli/                # CLI tool
│   ├── __init__.py
│   ├── __main__.py     # Entry: from cli.sk import main; main()
│   ├── sk.py           # Full CLI with argparse, cognitive state, LLM routing
│   ├── skill_loader.py # Skill discovery, YAML parsing, schema merging
│   ├── llm_client.py   # Multi-provider routing, model alias mapping
│   └── validator.py    # JSON Schema validation
├── graphs/             # Capability chaining
│   ├── routing_rules.yaml   # 13 trigger rules to capability entry points
│   └── capability_graph.yaml # 10 nodes, 5 workflow chains
├── infra/
│   └── cloudrun/
│       └── README.md
├── models/             # LLM-specific instruction files
│   ├── GEMINI.md
│   └── OPENAI.md
├── runtime/            # FastAPI service + cognitive pipeline
│   ├── __init__.py
│   ├── app.py          # FastAPI: /healthz, /readyz, /execute, /webhooks/notion
│   ├── auth.py         # Bearer token + HMAC-SHA256 webhook verification
│   ├── cognitive.py    # Energy routing, mode inference, model filtering
│   ├── config.py       # RuntimeSettings from env vars
│   ├── hooks.py        # 21 runtime hooks (all implemented, not stubs)
│   ├── hooks_scholar.py # Context monitoring, knowledge-inject
│   ├── init_hooks.py   # Hook initialization bridge
│   ├── middleware.py    # RequestID, structured logging, CORS, Server-Timing
│   ├── notion_client.py # Async Notion API client with retry/backoff
│   ├── pipeline_bridge.py # Webhook-to-skill routing
│   ├── planner.py      # Task planning from routing_rules + capability_graph
│   ├── sanitize.py     # Input sanitization (11 injection patterns)
│   ├── schemas.py      # Pydantic: ExecuteRequest, ExecuteResponse, CognitiveState
│   ├── validation.py   # Output validation against PROFILE.md contracts
│   ├── webhook_schemas.py # Notion webhook Pydantic models (28 event types)
│   └── webhooks.py     # Event router with LRU dedup cache
├── scripts/            # Diagnostics
│   ├── check_connections.py # Provider connectivity (config mode + live mode)
│   ├── smoke_runtime.py     # Post-deploy smoke tests
│   ├── syntax_audit.py      # Full codebase syntax validation
│   ├── parallel_audit.py
│   ├── review_codebase.py
│   └── validate_providers.py
├── skills/             # 47 skill definitions
│   ├── _base/
│   │   ├── schema_base.json  # Shared cognitive state schema (allOf base)
│   │   └── prompt_base.md
│   └── {domain}-{skill-name}/
│       ├── skill.yaml
│       ├── prompt.md
│       ├── schema.json
│       └── examples.json
├── tests/              # 12 test files, 184 tests
│   ├── test_auth.py
│   ├── test_cognitive.py
│   ├── test_cognitive_runtime.py
│   ├── test_github_pr_lister.py
│   ├── test_hooks.py
│   ├── test_planner.py
│   ├── test_router.py
│   ├── test_runtime_app.py
│   ├── test_sanitize.py
│   ├── test_schemas.py
│   ├── test_validation.py
│   └── test_webhooks.py
├── build.py            # Manifest generator: skill.yaml → OpenAI/Gemini JSON
├── AGENT.md            # Swarm orchestration protocol
├── CAPABILITIES.md
├── PROFILE.md          # Cognitive profile (loaded by all agents at session start)
├── README.md
├── SKILL.md            # 13 cognitive support skills (SK-DECOMP, SK-GATE, etc.)
├── TOOL.md
└── prompt.md           # Root prompt template
```

---

## Step 3: Cognitive Foundation Documents

These three markdown files define the cognitive contract. Every other component references them. Create them before writing any code.

### PROFILE.md

Cognitive profile template loaded at session start. Must define:

1. **Identity:** Primary operator, AuDHD-oriented defaults
2. **Cognitive Architecture** (6 sections):
   - Pattern Compression: verdict first, then model/assumptions/counterexamples/steps
   - Monotropism: single thread, one objective, one next action, announce shifts
   - Asymmetric Working Memory: full system first, then minimum sequencing, externalize aggressively
   - Interest-Based Nervous System: micro-steps for low-interest, novelty/urgency/meaning activate
   - Cognitive Load Management: surface 1 most critical, micro-sprint model, track completed not remaining
   - Executive Function: convert input to artifacts, minimize follow-ups, infer from context
3. **Output Constraints:** no em dashes (hard rule), no padding/filler, tables over paragraphs, strict parallel structure
4. **Honesty Protocol:** claim tags [OBS], [DRV], [GEN], [SPEC] for all factual claims
5. **Anti-Patterns:** no unsolicited encouragement, no medicalization, no "have you tried" basics, no em dashes
6. **Mode Routing:** 10 modes inferred from natural language (OSINT, Troubleshoot, Draft, Rewrite, Decide, Design, Summarize, Review, Chat, Execute)
7. **Output Templates:** Standard skeleton, Decision table, Troubleshooting triage, Chat mode

### AGENT.md

Swarm orchestration protocol. Must define:

1. **Topology:** Hub-and-spoke with orchestrator-managed autonomous handoffs
2. **Agent Registry:** 9 models with roles and primary domains
3. **Routing Matrix:** domain × tier (T1-T5) to model assignments with fallbacks
4. **Circuit Breakers:** cost ceiling, error spike, rate limit cascade, anomaly detector
5. **Cost Tracking:** per-model tier/cost, prefer cheapest model meeting tier requirement
6. **Task Classification (T1-T5):** trivial through critical, verification requirements
7. **Escalation Protocol:** 4 levels from retry to operator review

### SKILL.md

13 cognitive support skills (SK-* prefixed). Each skill defines: when to activate, output format, rules. Skills are cognitive augmentation patterns, not tasks.

| Skill ID | Purpose |
|----------|---------|
| SK-DECOMP | Task decomposition (3+ steps, max 7 subtasks) |
| SK-EXTERN | State externalization (implicit to explicit) |
| SK-RESUME | Session resume after 30+ min gap |
| SK-GATE | Decision gate for irreversible actions |
| SK-MICRO | Micro-step for low energy |
| SK-ANCHOR | Thread anchor for drift prevention |
| SK-VERIFY | Claim verification with honesty protocol |
| SK-BRIDGE | Context bridge for agent/session handoff |
| SK-CODEREVIEW | Code review with severity-ordered findings |
| SK-NUDGE | Behavioral nudge for task paralysis |
| SK-SYS-AUDIT | System API audit for degraded readiness |
| SK-SYS-RECOVER | Resource recovery for OOM threats |
| SK-A11Y | Accessibility gate (WCAG 2.2 AA) |

---

## Step 4: Shared Schema Base

Create `skills/_base/schema_base.json` first. Every skill schema extends it via `allOf`.

The base schema defines the cognitive_state contract with these exact 10 fields (must match runtime/schemas.py CognitiveState):

| Field | Type | Required | Values |
|-------|------|----------|--------|
| energy_level | string enum | yes | high, medium, low, crash |
| attention_state | string enum | yes | focused, diffuse, transitioning |
| session_context | string enum | no | new, resumed, interrupted |
| active_mode | string enum | no | osint, troubleshoot, draft, rewrite, decide, design, summarize, review, chat, execute |
| task_tier | string pattern | no | T1 through T5 |
| active_thread | string | no | Current monotropic focus thread |
| context_switches | integer | no | Topic switches in session (>2 triggers guard) |
| request_id | string | no | Unique request identifier |
| resume_from | string | no | Checkpoint ID for resumed sessions |
| resume_context | object | no | State from previous execution |

The base also defines skill_output requiring `cognitive_state_echo` and `next_action`.

---

## Step 5: Skill Definition Pattern

Each skill lives in `skills/{domain}-{skill-name}/` with exactly 4 files.

### skill.yaml (metadata and routing)

```yaml
name: {domain}-{skill-name}
display_name: Human Readable Name
description: >
  One-paragraph description of what this skill does.
version: "1.0.0"
category: {domain}
capabilities:
  - {capability}           # From: analyze, audit, evaluate, generate, optimize,
                           #       orchestrate, plan, research, synthesize, transform
models:
  primary: G-PRO31         # Model alias from adapters/config.yaml
  fallback: [G-PRO, O-54P]
sk_hooks:                  # Cognitive support skills to activate
  - SK-GATE
  - SK-VERIFY
inputs:
  - name: input_text
    type: string
    description: Primary input
    required: true
  - name: context
    type: string
    description: Additional context
    required: false
outputs:
  - name: result
    type: object
    description: Structured output
options:
  format:
    type: string
    enum: [full, summary, critical-only]
    default: full
```

### prompt.md (LLM instructions)

Every prompt follows this structure, grounded in cognitive patterns:

```markdown
## {Skill Display Name}

### Goal
{One sentence: what this skill produces}

## Energy Levels

### HIGH
- {Full execution: 3-5 detailed actions}

### MEDIUM
- {Standard execution: 2-3 actions}

### LOW
- {Minimal execution: 1-2 actions}

### CRASH
- Skip analysis. Record state to resume later.

## Cognitive State Branching
{How to start output based on cognitive state}

## Monotropism Guards
{Single-thread focus rules}

## Working Memory
{Externalization format: tables, checklists}

## Anti-pattern Section
{What to avoid, always includes "no em dashes"}

## Claim Tags
{Use [observed], [inferred], [general], [unverified]}

## Where Was I? Protocol
{State tracking header for context resume}

## Output JSON Format
{Exact JSON structure for skill output}
```

### schema.json (input/output validation)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "allOf": [
    { "$ref": "../_base/schema_base.json" },
    {
      "type": "object",
      "properties": {
        "input_text": {
          "type": "string",
          "description": "Skill-specific input description"
        }
      },
      "required": ["input_text"]
    }
  ]
}
```

### examples.json (test cases)

```json
[
  {
    "name": "Example scenario name",
    "input": {
      "input_text": "Concrete example input",
      "cognitive_state": {
        "energy_level": "medium",
        "attention_state": "focused"
      }
    },
    "expected_behavior": "Description of expected output"
  }
]
```

---

## Step 6: Model Registry

Create `adapters/config.yaml` with the 9-model registry across 2 providers.

| Alias | Provider | Model | Tier | Primary Use |
|-------|----------|-------|------|-------------|
| G-PRO | Google | gemini-2.5-pro | T3-T5 | Deep analysis, OSINT, research, multimodal |
| G-PRO31 | Google | gemini-3.1-pro-preview | T3-T5 | Primary for most skills, drafting, high-tier |
| G-FLA31 | Google | gemini-3.1-flash | T1-T2 | Fast analysis, triage, quick drafts |
| G-FLA | Google | gemini-2.5-flash | T1 | Budget triage |
| O-54P | OpenAI | gpt-5.4-pro | T4-T5 | Architecture, audit, planning, escalation |
| O-54 | OpenAI | gpt-5.4 | T3 | Creative, stakeholder comms, accessibility |
| O-53 | OpenAI | gpt-5.3 | T3 | Generalist fallback |
| O-CDX | OpenAI | gpt-5.3-codex | T3 | Code generation, automation |
| O-O4M | OpenAI | o4-mini | T1-T2 | Benchmarks, triage, structured checks |

The config also defines:
- Circuit breaker: failure_threshold=3, recovery_timeout=60s
- Energy-adaptive routing: high=T5 full, medium=T4 standard, low=T2 budget models only, crash=T1 no new work

---

## Step 7: Runtime (FastAPI)

### Pydantic Schemas (runtime/schemas.py)

Critical: CognitiveState must have exactly 10 fields matching schema_base.json.

Key models:
- `EnergyLevel` enum: HIGH, MEDIUM, LOW, CRASH
- `AttentionState` enum: FOCUSED, DIFFUSE, TRANSITIONING
- `SessionContext` enum: NEW, RESUMED, INTERRUPTED
- `CognitiveState`: 10-field model with validators
- `ExecuteRequest`: skill_id, input_text, cognitive_state, options, model_override, request_id (auto UUID)
- `ExecuteResponse`: output, model_used, provider, energy_level, tokens, latency_ms, hooks_executed, cognitive_compliance
- `CrashStateResponse`: checkpoint + resume_action (returned when energy=CRASH)

### FastAPI App (runtime/app.py)

4 endpoints:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /healthz | GET | None | Liveness probe |
| /readyz | GET | None | Readiness probe (provider health) |
| /execute | POST | Bearer | Skill execution with cognitive state |
| /webhooks/notion | POST | HMAC-SHA256 | Notion webhook receiver |

The /execute endpoint:
1. Validates ExecuteRequest
2. Checks energy level (CRASH returns CrashStateResponse immediately)
3. Runs hooks (always-on: reality-check, energy-route; plus skill-specific SK-* hooks)
4. Routes to LLM provider via SkillRouter
5. Validates output against PROFILE.md contracts
6. Returns ExecuteResponse with cognitive_state echo

### Hooks (runtime/hooks.py)

21 hooks, each fully implemented. 3 always-on (reality-check, energy-route, knowledge-inject). The hook system uses:
- `HOOK_REGISTRY`: dict mapping descriptive keys to hook functions
- `ALWAYS_ON_HOOKS`: list of hooks that run on every request
- `HookContext`: dataclass with skill_id, cognitive_state, input_text, prompt, options
- `HookResult`: dataclass with modified_input/prompt/options, gate_passed, validation_warnings
- `_resolve_hook_name()`: maps SK-* prefixed names to registry keys (SK-GATE to quality-gate, SK-VERIFY to verify)
- `run_hooks()`: executes hooks in order, accumulates results

### Other Runtime Files

- `auth.py`: Bearer token from AUDHD_API_KEYS env var, HMAC-SHA256 for webhooks
- `cognitive.py`: Energy-adaptive model filtering, mode inference from input text, cognitive preamble builder
- `middleware.py`: RequestID injection, structured JSON logging, CORS, Server-Timing headers
- `sanitize.py`: 11 injection pattern detectors (detection only, logs but passes through)
- `validation.py`: Output validation: no em dashes, no filler phrases, claim tags required for T3+, energy-appropriate length
- `webhooks.py`: 28 Notion event types, LRU dedup cache (10K entries, 1h TTL), category-based dispatch

---

## Step 8: Adapters (Provider Layer)

### base.py

Abstract `BaseAdapter` class with:
- `async def execute(prompt, model, config)` abstract method
- Circuit breaker (failure count, recovery timeout)
- Token counting interface
- Cost estimation interface

### openai_adapter.py

- Uses `AsyncOpenAI` client
- `chat.completions.create` with model, messages, tools
- Token extraction from response usage
- Circuit breaker integration

### google_adapter.py

- Uses `google.genai` client
- Supports both Gemini API and Vertex AI backends
- `GenerateContentConfig` with thinking_config support
- Token extraction, cost estimation
- Multi-backend routing based on GOOGLE_GENAI_USE_VERTEXAI

### router.py (SkillRouter)

Central execution orchestrator:
1. Load skill definition (skill.yaml + prompt.md)
2. Resolve model from skill primary/fallback chain
3. Apply energy-adaptive filtering (crash=reject, low=budget models only)
4. Build prompt with cognitive preamble
5. Execute via appropriate adapter
6. Handle failover on provider errors
7. Return structured response

---

## Step 9: Agent Compositions

9 domain agents in `agents/`, each with 8 files:

| Agent | Domain |
|-------|--------|
| engineer | Cross-discipline coordination |
| software-engineer | Application development |
| data-engineer | Data pipelines, ETL, warehousing |
| devops-engineer | Infrastructure, CI/CD |
| ai_ml_engineer | ML systems, training |
| hardware-engineer | Hardware design |
| network-engineer | Network architecture |
| secops-engineer | Security operations |
| ui-engineer | Frontend, UX |

### agent.yaml structure

```yaml
agent:
  name: {domain}-engineer
  display_name: "Display Name"
  version: "1.0.0"
  description: >-
    Domain description for AuDHD Cognitive Swarm.
  domain: {domain_name}
  cognitive_profile:
    patterns:
      - pattern_compression
      - monotropism
      - asymmetric_working_memory
      - meta_layer_reflex
    energy_model: true
    externalization: required

skills:
  always_on:
    - reality_check
    - energy_routing
    - externalization
  domain:
    - {domain_skill_1}
    - {domain_skill_2}

model_routing:
  google:
    default_model: gemini-3.1-pro-preview
    fallback_chain: [...]
    models:
      {model_id}:
        role: {role}
        tier: {1-4}
        routing_notes: >-
          When to use this model for this domain.
  openai:
    default_model: gpt-5.3-codex
    fallback_chain: [...]
    models: {...}

energy_routing:
  high: {full execution models and tasks}
  medium: {standard models and tasks}
  low: {budget models and tasks}
  crash: {triage only}

handoff:
  accepts_from: [list of agents]
  delegates_to:
    - {agent}: [{task_types}]
  protocol: HANDOFF
  format: structured_yaml
```

---

## Step 10: Build System and CLI

### build.py

Reads skill definitions and generates LLM-specific manifests:
- Loads 4 canonical files per skill (skill.yaml, prompt.md, schema.json, examples.json)
- Resolves allOf/$ref in JSON schemas to flat structure
- Generates `dist/openai/{skill}.json` and `dist/gemini/{skill}.json`
- Aggregates into `dist/{adapter}/manifest.json`
- Supports: `--skill {name}`, `--adapter {openai|gemini}`, `--external-skills {path}`

### CLI (cli/sk.py)

Full CLI with argparse:
- `sk {skill-name} "{input}" [--focus {area}] [--energy {level}] [--dry-run]`
- `sk --list` to list available skills
- Builds cognitive state from flags
- Routes through LLM client
- Formats output

### CLI entry (sk)

Bash wrapper at repo root:
```bash
#!/usr/bin/env bash
python -m cli "$@"
```

---

## Step 11: Capabilities and Graphs

### 10 Capability YAMLs (capabilities/)

Each defines: name, description, inputs, outputs, and skill assignments (primary + secondary).

Capabilities: analyze, audit, evaluate, generate, optimize, orchestrate, plan, research, synthesize, transform.

### Routing Rules (graphs/routing_rules.yaml)

13 trigger rules mapping keywords to capability entry points:
- "research", "investigate" routes to research capability
- "review", "audit" routes to analyze capability
- "build", "code" routes to generate capability

### Capability Graph (graphs/capability_graph.yaml)

10 capability nodes with inputs/outputs and 5 predefined workflow chains:
- research_to_report: research then analyze then synthesize
- build_and_validate: plan then generate then evaluate then optimize
- code_review_pipeline, content_pipeline, security_pipeline

---

## Step 12: Tests

12 test files covering every runtime component. All use pytest with pytest-asyncio.

| Test File | What It Tests |
|-----------|---------------|
| test_auth.py | Bearer token verification, HMAC webhook auth |
| test_cognitive.py | Cognitive state management, energy routing |
| test_cognitive_runtime.py | End-to-end cognitive pipeline |
| test_hooks.py | All 21 hooks, ALWAYS_ON behavior, SK-* resolution |
| test_schemas.py | Pydantic model validation, CognitiveState 10-field alignment |
| test_validation.py | Output validation (em dashes, filler, claim tags) |
| test_sanitize.py | Injection pattern detection |
| test_router.py | Skill routing, model failover |
| test_runtime_app.py | FastAPI endpoint integration |
| test_webhooks.py | Webhook routing, dedup cache |
| test_planner.py | Task planning, capability routing |
| test_github_pr_lister.py | GitHub PR listing skill |

Run: `pytest -q` (all 184 tests should pass in under 3 seconds).

---

## Step 13: CI/CD

### .github/workflows/python-package.yml

Triggers: push to main, pull_request to main.

Steps:
1. Checkout, setup Python 3.11
2. `pip install -e ".[dev]"`
3. Compile Python sources
4. Validate config: `python scripts/check_connections.py --mode config`
5. Rebuild manifests: `python build.py`
6. Fail on dist drift: `git diff --exit-code -- dist`
7. Run tests: `pytest -q`

### .github/workflows/deploy-cloud-run.yml

Triggers: workflow_dispatch, tag push (v*).

Jobs: build-image, deploy-staging, smoke-staging, deploy-production (optional).

---

## Step 14: Skill Domains

47 skills across 9 domains. Create the skeleton for each:

| Domain | Count | Skills |
|--------|-------|--------|
| engineering | 16 | code-reviewer, security-engineer, devops-automator, github-pr-lister, software-architect, database-optimizer, frontend-developer, technical-writer, git-workflow-master, incident-response-commander, rapid-prototyper, autonomous-optimization, ai-engineer, data-engineer, ai-data-remediation, lsp-index-engineer |
| design | 7 | ux-architect, ui-designer, brand-guardian, inclusive-visuals-specialist, ux-researcher, visual-storyteller, image-prompt-engineer |
| testing | 7 | reality-checker, accessibility-auditor, performance-benchmarker, api-tester, evidence-collector, test-results-analyzer, tool-evaluator |
| product | 4 | sprint-prioritizer, feedback-synthesizer, trend-researcher, behavioral-nudge-engine |
| support | 2 | analytics-reporter, compliance-auditor |
| marketing | 1 | content-creator |
| project-management | 3 | experiment-tracker, project-shepherd, project-manager-senior |
| specialized | 6 | developer-advocate, document-generator, mcp-builder, model-qa, agents-orchestrator, corporate-training |
| automation | 1 | automation-governance |

---

## Scaffolding Order (Minimizing Effort)

Execute in this order. Each step unlocks the next.

1. **Root config** (pyproject.toml, .env.example, .gitignore, Dockerfile): 4 files, enables install
2. **Cognitive contracts** (PROFILE.md, AGENT.md, SKILL.md): 3 files, defines all behavior rules
3. **Base schema** (skills/_base/schema_base.json): 1 file, unlocks all skill schemas
4. **Runtime schemas** (runtime/schemas.py): 1 file, must align 10 fields with base schema
5. **Adapters config** (adapters/config.yaml): 1 file, defines all model aliases
6. **Runtime core** (app.py, auth.py, cognitive.py, config.py, middleware.py): 5 files, working API
7. **Hooks** (hooks.py, hooks_scholar.py, init_hooks.py): 3 files, cognitive augmentation pipeline
8. **Adapters** (base.py, router.py, openai_adapter.py, google_adapter.py): 4 files, LLM execution
9. **Validation + sanitize** (validation.py, sanitize.py): 2 files, output contracts
10. **Webhooks** (webhooks.py, webhook_schemas.py, notion_client.py, pipeline_bridge.py): 4 files, event system
11. **CLI** (sk.py, skill_loader.py, llm_client.py, validator.py, __main__.py, sk wrapper): 6 files
12. **Build system** (build.py): 1 file, manifest generation
13. **One reference skill** (engineering-code-reviewer): 4 files, validates full pipeline
14. **Tests** (12 files): validates everything
15. **Remaining 46 skills**: bulk generation from reference pattern
16. **9 agent compositions**: bulk generation from data-engineer pattern
17. **Capabilities + graphs**: 12 files, orchestration layer
18. **Scripts**: diagnostics and validation tooling
19. **CI/CD workflows**: 2 files

---

## Reality Check: What This Document Claims

Every claim in this document was verified against the actual repository on the date of writing:

| Claim | Verification |
|-------|-------------|
| 47 skills, all with 4 files | `ls skills/ \| grep -v _base \| wc -l` returns 47; zero missing files |
| 184 tests passing | `pytest -q` returns "184 passed in 2.38s" |
| Build produces 47 tools | `python build.py` returns "Built: 47 \| Errors: 0" |
| Syntax audit clean | `python scripts/syntax_audit.py` returns "STATUS: HEALTHY" |
| 0 stub files in runtime | grep for TODO/FIXME/NotImplementedError/pass-as-body returns 0 matches |
| 9 agents × 8 files each | `find agents/ -type f \| wc -l` confirms 73 files (72 + 1 README) |
| 10 capability YAMLs | `ls capabilities/ \| wc -l` returns 10 |
| 21 hooks implemented | HOOK_REGISTRY in hooks.py has 21 entries, all with function bodies |
| CognitiveState has 10 fields | runtime/schemas.py and schema_base.json aligned 10/10 |
| README says 47 skills | [OBS] README.md updated to match actual count of 47. |

---

## License

MIT. This is open source cognitive augmentation for AuDHD adults. Not medical software. Not safety scaffolding. Competent adult tooling.
