# audhd-agents

Multi-agent orchestration designed for AuDHD cognition. Nine LLM instances, 52 skills, 21 runtime hooks, energy-adaptive routing, and a FastAPI service with output validation.

Every design decision maps to a real cognitive pattern: monotropism, pattern compression, asymmetric working memory, interest-based activation, executive function offload. This is cognitive augmentation for a competent adult, not safety scaffolding.

MIT License

## How it works

```
Operator input + cognitive_state
        |
   [ Router ]  reads energy/mode/tier, selects model chain
        |
   [ Hooks ]   21 hooks (3 always-on: reality-check, energy-route, knowledge-inject)
        |
   [ Provider ] OpenAI or Google adapter executes against chosen model
        |
   [ Validation ] checks output against PROFILE.md contracts
        |
   Response + cognitive_state echo
```

Crash mode short-circuits the pipeline: saves state, returns one sentence, stops.

## Setup

```bash
git clone https://github.com/AICincy/audhd-agents
cd audhd-agents
pip install -e ".[dev]"
cp .env.example .env
```

Add your API keys to `.env`:

```bash
OPENAI_API_KEY=sk-...           # required
GOOGLE_API_KEY=AIza...          # required (or use Vertex AI below)
```

Verify:

```bash
python scripts/check_connections.py --mode config   # config check, no API calls
python scripts/check_connections.py --mode live      # live connection test
pytest -q                                            # 150 tests
python build.py                                      # generate dist/ manifests
```

## Models

Nine models registered in [`adapters/config.yaml`](adapters/config.yaml). Full routing matrix and circuit breakers in [AGENT.md](AGENT.md).

| Alias | Model | Provider | Tier | Role |
|-------|-------|----------|------|------|
| G-PRO31 | gemini-3.1-pro-preview | Google | T3 | Deep analyst, OSINT, drafting |
| G-PRO | gemini-2.5-pro | Google | T3 | Research, multimodal, data analysis |
| G-FLA31 | gemini-3.1-flash | Google | T1 | Triage, fast drafts, analysis |
| G-FLA | gemini-2.5-flash | Google | T1 | Fast/cheap, STT cleanup, TTS prep |
| O-54P | gpt-5.4-pro | OpenAI | T5 | Deep planning, audit synthesis |
| O-54 | gpt-5.4 | OpenAI | T3 | Ideation, creative, stakeholder comms |
| O-53 | gpt-5.3 | OpenAI | T3 | Generalist overflow, fallback |
| O-CDX | gpt-5.3-codex | OpenAI | T3 | Code generation, automation |
| O-O4M | o4-mini | OpenAI | T1 | Rapid verification, benchmarks |

### Energy-adaptive routing

| Energy | Max tier | Behavior |
|--------|----------|----------|
| High | T5 | Full execution, all models available |
| Medium | T4 | Standard, prefer fast models for T1-T2 |
| Low | T2 | Gemini + o4-mini only, 3 bullets max |
| Crash | T1 | No new work. Save state. Stop. |

## Skills

52 skills across 9 domains, each defined by four files:

| Domain | Count | Examples |
|--------|-------|---------|
| Engineering | 17 | code-reviewer, software-architect, security-engineer, devops-automator, github-pr-lister |
| Testing | 8 | reality-checker, accessibility-auditor, performance-benchmarker |
| Design | 7 | ux-architect, ui-designer, brand-guardian, inclusive-visuals |
| Specialized | 6 | agents-orchestrator, mcp-builder, model-qa |
| Product | 4 | sprint-prioritizer, feedback-synthesizer, trend-researcher |
| Support | 4 | compliance-auditor, legal-compliance-checker, analytics-reporter |
| Project Mgmt | 3 | project-shepherd, experiment-tracker |
| Marketing | 2 | content-creator, linkedin-content-creator |
| Automation | 1 | automation-governance |

Each skill has: `skill.yaml` (definition), `prompt.md` (prompt logic), `schema.json` (validation), `examples.json` (test cases).

All skills reference `G-PRO31` as primary model with `[G-PRO, O-54P]` fallback chain.

Build manifests for OpenAI and Gemini formats:

```bash
python build.py    # outputs to dist/
```

## Hooks

21 runtime hooks executed via `run_hooks()` in the router pipeline. Three are always-on and fire on every execution regardless of skill configuration.

| Hook | Phase | Always-on |
|------|-------|-----------|
| reality-check | prompt_injection | Yes |
| energy-route | prompt_injection | Yes |
| knowledge-inject | pre_execute | Yes |
| decompose | pre_execute | |
| bridge | pre_execute | |
| speech-input | pre_execute | |
| quality-gate | prompt_injection | |
| verify | prompt_injection | |
| focus | prompt_injection | |
| format | prompt_injection | |
| load-skill | prompt_injection | |
| micro-step | prompt_injection | |
| anchor | prompt_injection | |
| code-review | prompt_injection | |
| refocus | prompt_injection | |
| accessibility | prompt_injection | |
| system-audit | prompt_injection | |
| tone | prompt_injection | |
| resume | on_resume | |
| recover | on_error | |
| speech-output | post_execute | |

Output validation (`runtime/validation.py`) runs after every model call and checks: no em dashes, no filler phrases, no unsolicited motivation, claim tags present for T3+ output, energy-appropriate length.

## Runtime API

```bash
uvicorn runtime.app:app --host 0.0.0.0 --port 8080
```

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/healthz` | GET | None | Process health |
| `/readyz` | GET | None | Router, provider, skill readiness |
| `/execute` | POST | Bearer | Skill execution with cognitive state |
| `/webhooks/notion` | POST | HMAC | Notion webhook receiver |

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `staging` | `staging` or `production` |
| `REQUIRED_PROVIDERS` | `openai,google` | Providers that must be healthy |
| `LOG_LEVEL` | `INFO` | Logging level |
| `AUDHD_API_KEYS` | (empty) | Comma-separated bearer tokens for `/execute` |
| `NOTION_WEBHOOK_SECRET` | (empty) | HMAC-SHA256 signing secret for webhooks |

## CLI

```bash
sk engineering-code-reviewer "Review this PR diff" --focus security
sk engineering-ai-engineer "Build a rec system" --energy low --tier T2
sk --list
cat diff.txt | sk engineering-code-reviewer --format critical-only
```

The CLI calls `validate_output()` on every response and prints violations to stderr.

## Google auth options

| Mode | Required variables |
|------|--------------------|
| Gemini Developer API | `GOOGLE_API_KEY` |
| Vertex Express | `GOOGLE_GENAI_USE_VERTEXAI=true`, `VERTEX_API_KEY` |
| Vertex Standard (ADC) | `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` |

## Cognitive architecture

Five patterns from [PROFILE.md](PROFILE.md):

- **Monotropism**: one thread, one objective, one next action. Topic shift requires announcement.
- **Pattern compression**: verdict first, then model, assumptions, counterexamples, execution steps.
- **Asymmetric working memory**: full system view before sequencing. Tables over prose. State externalized.
- **Interest-based activation**: micro-steps for low-interest tasks. Smallest possible first action.
- **Executive function offload**: infer and execute. Questions are a last resort.

Claim tags enforced on T3+ output: `[observed]`, `[inferred]`, `[general]`, `[unverified]`.

## Project structure

```
adapters/           Provider layer (router, OpenAI, Google adapters, config)
runtime/            FastAPI service, hooks, validation, cognitive pipeline, schemas
skills/             52 skill definitions (skill.yaml, prompt.md, schema.json, examples.json)
cli/                sk command-line tool
scripts/            Diagnostics, smoke tests, provider validation
tests/              150 tests
models/             LLM-specific instruction files (GEMINI.md, OPENAI.md)
capabilities/       Capability definitions (YAML)
graphs/             Capability chaining
infra/cloudrun/     Cloud Run deployment config
build.py            Manifest generator (outputs to dist/)
```

## Deployment

Dockerfile and GitHub Actions workflows exist. Cloud Run deployment scaffolding in `infra/cloudrun/`.

```bash
docker build -t audhd-agents .
```

See [infra/cloudrun/README.md](infra/cloudrun/README.md) for secrets, variables, and runtime defaults.

## Related

- [AICincy/audhd-skills](https://github.com/AICincy/audhd-skills) — skill prompt templates and cognitive augmentation layer
- [AGENT.md](AGENT.md) — routing matrix, circuit breakers, escalation protocol, cost tracking
- [PROFILE.md](PROFILE.md) — cognitive profile and output constraints
- [GROUNDING.md](https://github.com/AICincy/audhd-skills/blob/main/GROUNDING.md) — what every component actually does vs. aspirational

## Contributing

Contributions welcome, especially from neurodivergent developers. Fork [PROFILE.md](PROFILE.md) and adapt to your own cognitive patterns.

[Open an issue](https://github.com/AICincy/audhd-agents/issues) for bugs, skill requests, or profile adaptations.
