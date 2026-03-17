# audhd-agents

Multi-agent orchestration designed for AuDHD cognition. Nine models across two providers, 47 skills (with subskill routing), 23 runtime hooks, energy-adaptive routing, chain-of-thought reasoning, retrieval-augmented generation, and a FastAPI service with output validation.

Every design decision maps to a real cognitive pattern: monotropism, pattern compression, asymmetric working memory, interest-based activation, executive function offload. Cognitive augmentation for a competent adult, not safety scaffolding.

MIT License

## How it works

```
Operator input + cognitive_state
        |
   [ Router ]     reads energy/mode/tier, selects model chain
        |
   [ Hooks ]      23 hooks (3 always-on: reality-check, energy-route, knowledge-inject)
        |                   COT reasoning + RAG context injected here
        |
   [ Provider ]   OpenAI or Google adapter executes against chosen model
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

Add API keys to `.env`:

```bash
OPENAI_API_KEY=sk-...           # required
GOOGLE_API_KEY=AIza...          # required (or use Vertex AI below)
```

Verify:

```bash
python scripts/check_connections.py --mode config   # config check, no API calls
python scripts/check_connections.py --mode live      # live connection test
pytest -q                                            # 184 tests
python build.py                                      # generate dist/ manifests
```

## Models

Nine models in [`adapters/config.yaml`](adapters/config.yaml). Full routing matrix and circuit breakers in [AGENT.md](AGENT.md).

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

47 skills across 9 domains. Each skill has four files: `skill.yaml` (config), `prompt.md` (prompt), `schema.json` (validation), `examples.json` (test cases).

| Domain | Count | Examples |
|--------|-------|---------|
| Engineering | 16 | code-reviewer, software-architect, security-engineer, devops-automator, github-pr-lister |
| Design | 7 | ux-architect, ui-designer, brand-guardian, inclusive-visuals-specialist |
| Testing | 7 | reality-checker, accessibility-auditor, performance-benchmarker, evidence-collector |
| Specialized | 6 | agents-orchestrator, mcp-builder, model-qa, corporate-training |
| Product | 4 | sprint-prioritizer, feedback-synthesizer, trend-researcher |
| Project Mgmt | 3 | project-shepherd, experiment-tracker, project-manager-senior |
| Support | 2 | compliance-auditor, analytics-reporter |
| Marketing | 1 | content-creator (with linkedin subskill) |
| Automation | 1 | automation-governance |

### Subskill routing

Dominant skills absorb related skills as subskills, reducing redundancy while preserving specialized behavior. Subskills are declared in `skill.yaml` and routed via the `subskill` field in `schema.json`.

| Dominant Skill | Subskill | Absorbed From |
|---------------|----------|---------------|
| engineering-software-architect | backend | engineering-backend-architect |
| compliance-auditor | legal-review | support-legal-compliance-checker |
| marketing-content-creator | linkedin | marketing-linkedin-content-creator |
| engineering-autonomous-optimization | workflow | testing-workflow-optimizer |
| support-analytics-reporter | executive-summary | support-executive-summary-generator |

All skills reference `G-PRO31` as primary model with `[G-PRO, O-54P]` fallback chain.

```bash
python build.py    # outputs to dist/
```

## Hooks

23 runtime hooks executed via `run_hooks()` in the router pipeline. Three always-on hooks fire on every execution regardless of skill configuration.

| Hook | Type | Always-on | Description |
|------|------|-----------|-------------|
| reality-check | prompt | Yes | Validates claims, flags drift/hallucination (RC-001 through RC-005) |
| energy-route | prompt | Yes | Enforces energy-appropriate output density |
| knowledge-inject | pre-execute | Yes | Injects domain knowledge context |
| chain-of-thought | prompt | | Structured reasoning: lightweight/standard/deep by tier |
| retrieval-context | prompt | | RAG: grounds responses in retrieved documents |
| decompose | pre-execute | | Breaks T4+ tasks into parallel sub-tasks |
| bridge | pre-execute | | Cross-skill context relay |
| quality-gate | prompt | | Blocks output below quality threshold |
| verify | prompt | | Post-generation claim verification |
| focus | prompt | | Monotropism guard (context switch detection) |
| format | prompt | | Output structure enforcement |
| code-review | prompt | | Code-specific review scaffolding |
| accessibility | prompt | | WCAG/a11y compliance checking |
| system-audit | prompt | | System-wide audit protocol |
| speech-input | pre-execute | | STT preprocessing |
| speech-output | post-execute | | TTS postprocessing |
| tone | prompt | | Register/formality adaptation |
| load-skill | prompt | | External VoltAgent skill bridge |
| resume | on-resume | | Where Was I? protocol |
| micro-step | prompt | | Low-interest task decomposition |
| anchor | prompt | | Thread anchoring for monotropism |
| refocus | prompt | | Attention redirection nudge |
| recover | on-error | | Error recovery and state save |

Skills opt into hooks via `sk_hooks` in their `skill.yaml` using SK-* aliases (e.g., `SK-COT`, `SK-RAG`, `SK-GATE`).

### Chain of Thought (SK-COT)

Injects structured reasoning scaffolding adapted to task complexity:

| Tier | Mode | Steps |
|------|------|-------|
| T1-T2 | Lightweight | Observe, Decide, Act |
| T3 | Standard | Decompose, Reason, Synthesize, Verify |
| T4-T5 | Deep | Hypothesize, Evidence for/against, Alternatives, Synthesize, Verify |

Energy gating: LOW and CRASH skip COT (direct answer preferred).

### Retrieval-Augmented Generation (SK-RAG)

Injects retrieved documents into the prompt as grounded context. All RAG-sourced claims must be tagged `[observed]`.

```json
{
  "retrieval_context": [
    {"source": "architecture.md", "content": "...", "relevance_score": 0.95},
    {"source": "api-spec.yaml", "content": "..."}
  ]
}
```

Energy gating: LOW limits to 3 chunks. CRASH skips RAG entirely.

Output validation (`runtime/validation.py`) runs after every model call: no em dashes, no filler, no unsolicited motivation, claim tags present for T3+, energy-appropriate length.

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
| Vertex AI (ADC) | `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` |

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
skills/             47 skill definitions (skill.yaml, prompt.md, schema.json, examples.json)
  _base/            Shared schema and prompt base (COT, RAG, cognitive state)
cli/                sk command-line tool
scripts/            Diagnostics, smoke tests, provider validation
tests/              184 tests
models/             LLM-specific instruction files (GEMINI.md, OPENAI.md)
capabilities/       Capability definitions (10 capabilities across 47 skills)
graphs/             Capability chaining and routing rules
infra/cloudrun/     Cloud Run deployment config
build.py            Manifest generator (outputs to dist/)
```

## Deployment

Dockerfile and GitHub Actions workflows provided. Cloud Run deployment scaffolding in `infra/cloudrun/`.

```bash
docker build -t audhd-agents .
```

See [infra/cloudrun/README.md](infra/cloudrun/README.md) for secrets, variables, and runtime defaults.

## Related

- [AICincy/audhd-skills](https://github.com/AICincy/audhd-skills): skill prompt templates and cognitive augmentation layer
- [AGENT.md](AGENT.md): routing matrix, circuit breakers, escalation protocol, cost tracking
- [PROFILE.md](PROFILE.md): cognitive profile and output constraints
- [SUGGESTIONS.md](SUGGESTIONS.md): improvement proposals ranked by effort and impact

## Contributing

Contributions welcome, especially from neurodivergent developers. Fork [PROFILE.md](PROFILE.md) and adapt to your own cognitive patterns.

[Open an issue](https://github.com/AICincy/audhd-agents/issues) for bugs, skill requests, or profile adaptations.
