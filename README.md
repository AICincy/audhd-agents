# AUDHD Cognitive Swarm Protocol

Multi-agent orchestration for AuDHD cognition. 11 models, skill-based augmentation, LLM-specific adapters.

Built by neurodivergent engineers for neurodivergent engineers.

## Architecture

```
audhd-agents/
├── PROFILE.md                    # Cognitive profile + constraints
├── AGENT.md                      # Swarm orchestration + routing
├── TOOL.md                       # Tool contracts + errors
├── SKILL.md                      # Cognitive skills (SK-*)
├── models/
│   ├── ANTHROPIC.md              # Anthropic adapter instructions
│   ├── CLAUDE.md                 # Claude instructions
│   ├── GEMINI.md                 # Gemini instructions
│   └── OPENAI.md                 # GPT instructions
├── capabilities/                 # Capability definitions
├── skills/                       # Skill definitions
│   └── {skill-name}/
│       ├── skill.yaml            # Definition
│       ├── prompt.md             # Prompt
│       ├── schema.json           # Schema
│       └── examples.json         # Tests
├── graphs/                       # Capability chaining
├── agents/                       # Agent compositions
├── adapters/
│   ├── skill.yaml                # Adapter layer skill definition
│   ├── schema.json               # Adapter invocation schema
│   ├── config.yaml               # Provider config
│   ├── router.py                 # Router with failover
│   ├── anthropic_adapter.py      # Claude adapter
│   ├── openai_adapter.py         # OpenAI adapter
│   └── google_adapter.py         # Gemini adapter
├── runtime/                      # FastAPI runtime
├── scripts/                      # Build and diagnostics
├── dist/                         # Generated manifests
├── .vscode/                      # VS Code config
└── build.py                      # Build script
```

## Models (11)

| **ID** | **Model** | **Role** |
| --- | --- | --- |
| C-OP46 | Claude Opus 4.6 | Deep Analyst (Primary) |
| C-OP45 | Claude Opus 4.5 | Deep Analyst (Fallback) |
| C-SN46 | Claude Sonnet 4.6 | Rapid Executor (Primary) |
| C-SN45 | Claude Sonnet 4.5 | Rapid Executor (Fallback) |
| G-PRO | Gemini 2.5 Pro | Knowledge Integrator |
| O-54 | GPT-5.4 | Ideation Engine (Primary) |
| O-53 | GPT-5.3 | Ideation Engine (Fallback) |
| O-54P | GPT-5.4 Pro | Deep Planner |
| O-CDX | GPT-5.3 Codex | Code Automator |
| O-O4M | o4-mini | Rapid Verifier |
| O-MAX | GPT Max | Generalist Overflow |

## Cognitive Design Principles

Designed to match AuDHD cognitive patterns:

- **Monotropism:** Single-thread control. Autonomous handoffs via orchestrator only.
- **Pattern compression:** Verdict first, structure second.
- **Asymmetric working memory:** Maps over turn-by-turn. Full view before sequencing.
- **Interest-based activation:** Micro-sprints, momentum tracking, smallest-first actions.
- **Executive function offload:** Agents infer and execute. Questions are a last resort.

## Skill System (AIO)

Each skill has a canonical definition that builds to 3 LLM formats:

- **skill.yaml**: Name, description, capabilities, inputs, outputs, mappings
- **prompt.md**: Prompt logic with goal, rules, workflow, output
- **schema.json**: Schema for validation
- **examples.json**: Test invocations

51 skills across engineering, design, testing, PM, marketing, and specialized domains.

Run `python build.py` to generate `dist/` manifests.

## Setup

1. Clone repo
2. Open in VS Code
3. `cp .env.example .env` and add API keys
4. `pip install -r requirements.txt`
5. `python build.py` to generate `dist/` files
6. Config diagnostics: `python scripts/check_connections.py --mode config`
7. Live diagnostics: `python scripts/check_connections.py --mode live`

Google support:

- Gemini API via `GOOGLE_API_KEY`
- Vertex Express via `GOOGLE_GENAI_USE_VERTEXAI=true` and `VERTEX_API_KEY`
- Vertex standard via `GOOGLE_GENAI_USE_VERTEXAI=true` plus `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and auth credentials

## Private Runtime

Production runs on a FastAPI service.

- `GET /healthz`: Process health
- `GET /readyz`: Router, provider, skill readiness
- `POST /execute`: Authenticated skill execution

Run locally:

```
uvicorn runtime.app:app --host 0.0.0.0 --port 8080
```

Runtime environment variables:

- `APP_ENV=staging|production`
- `REQUIRED_PROVIDERS=openai,anthropic,google`
- `LOG_LEVEL=INFO|DEBUG|WARNING`

`/readyz` checks config only. Use `python scripts/check_connections.py --mode live` as a release gate.

## Production Delivery

Deployed to Cloud Run.

- Private authenticated service
- Secret Manager for credentials
- GitHub Actions deploys via Workload Identity
- Staging deploy and smoke test before production
- Production reuses staging image digest

See [infra/cloudrun/README.md](infra/cloudrun/README.md) for GitHub variables, secrets, and runtime defaults.

## Loading Order (All Models)

1. `PROFILE.md` (cognitive profile, constraints)
2. Model-specific file (`models/CLAUDE.md`, `models/GEMINI.md`, or `models/OPENAI.md`)
3. `SKILL.md` (cognitive skills)
4. `TOOL.md` (on first tool invocation)

## Contributing

Contributions welcome, especially from neurodivergent developers. Fork [PROFILE.md](PROFILE.md) and adapt it to your patterns.
