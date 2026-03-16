# audhd-agents

Multi-agent orchestration for AuDHD cognition. Hub-and-spoke swarm across 9 LLM instances, 51 skills, energy-adaptive routing, and a FastAPI runtime with output validation.

Built by a neurodivergent engineer, for neurodivergent engineers. Every design decision maps to a real cognitive pattern: monotropism, pattern compression, asymmetric working memory, interest-based activation.

MIT License — [AICincy](https://github.com/AICincy)

---

## How It Works

1. **Operator sends input** with optional `cognitive_state` (energy level, focus mode, task tier)
2. **Router** reads cognitive state, classifies task tier (T1–T5), selects model from the routing matrix
3. **Hooks** run pre-execution (speech cleanup, task decomposition, reality-check injection, energy routing)
4. **Skill** executes against the chosen provider (OpenAI or Google)
5. **Validation** checks output against PROFILE.md contracts (no em dashes, no filler, claim tagging)
6. **Response** echoes cognitive state back for orchestrator continuity

Crash mode short-circuits everything: saves state, returns one sentence, stops.

---

## Agent Registry (9 models)

| ID | Model | Role | Tier |
|----|-------|------|------|
| G-PRO | Gemini 2.5 Pro | Deep Analyst / Integrator | T3–T5 |
| G-PRO31 | Gemini 3.1 Pro Preview | Deep Analyst / Integrator | T3–T5 |
| G-FLA31 | Gemini 3.1 Flash | Rapid Verifier / Analyst | T1–T3 |
| O-54P | GPT-5.4 Pro | Deep Planner / Analyst | T4–T5 |
| O-54 | GPT-5.4 | Ideation Engine (Primary) | T2–T4 |
| O-53 | GPT-5.3 | Ideation Engine (Fallback) | T2–T4 |
| O-CDX | GPT-5.3 Codex | Code Automator | T2–T4 |
| O-O4M | o4-mini | Rapid Verifier | T1–T2 |
| O-MAX | GPT Max | Generalist Overflow | T2–T4 |

Routing matrix, circuit breakers, and escalation protocol are in [AGENT.md](AGENT.md).

---

## Skills (51)

Skills are defined in `skills/{name}/` with four files each:

| File | Purpose |
|------|---------|
| `skill.yaml` | Name, description, capabilities, inputs, outputs |
| `prompt.md` | Prompt logic: goal, rules, workflow, output format |
| `schema.json` | JSON Schema for input/output validation |
| `examples.json` | Test invocations |

Skill domains: engineering, design, testing, product, marketing, project management, specialized.

`python build.py` generates `dist/` manifests in OpenAI, Gemini, and canonical formats.

---

## Setup

### Requirements

- Python 3.11+
- OpenAI API key (required)
- Google API key or Vertex AI credentials (required)

### Install

```bash
git clone https://github.com/AICincy/audhd-agents
cd audhd-agents
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Optional: Vertex AI instead of Gemini Developer API
GOOGLE_GENAI_USE_VERTEXAI=false
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=   # path to service account JSON

# Optional: Vertex Express Mode (API key auth, no ADC)
VERTEX_API_KEY=

# API auth for /execute endpoint (leave empty to disable in dev)
AUDHD_API_KEYS=

# Webhook signing secret for Notion integration
NOTION_WEBHOOK_SECRET=
```

### Verify

```bash
# Check config (no live calls)
python scripts/check_connections.py --mode config

# Live connection test (makes real API calls)
python scripts/check_connections.py --mode live

# Run tests
pytest -q
```

### Build skill manifests

```bash
python build.py
# Outputs to dist/ (not committed)
```

---

## Runtime (FastAPI)

```bash
uvicorn runtime.app:app --host 0.0.0.0 --port 8080
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Process health |
| `/readyz` | GET | Router, provider, and skill readiness |
| `/execute` | POST | Authenticated skill execution |

**Runtime environment variables:**

| Variable | Values | Default |
|----------|--------|---------|
| `APP_ENV` | `staging`, `production` | `staging` |
| `REQUIRED_PROVIDERS` | comma-separated provider names | `openai,google` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` | `INFO` |

`/readyz` checks config only — it does not make live API calls. Use `python scripts/check_connections.py --mode live` as your release gate.

---

## Google Provider Options

Three mutually exclusive auth paths:

| Mode | Variables Required |
|------|--------------------|
| Gemini Developer API | `GOOGLE_API_KEY` |
| Vertex Express (API key) | `GOOGLE_GENAI_USE_VERTEXAI=true`, `VERTEX_API_KEY` |
| Vertex Standard (ADC) | `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` |

The adapter auto-selects Vertex when a Vertex-specific credential is present. Set `GOOGLE_GENAI_USE_VERTEXAI=true` to force it.

---

## Cognitive Architecture

Five cognitive patterns drive every design decision:

| Pattern | Implementation |
|---------|---------------|
| **Monotropism** | One active thread. Orchestrator-managed handoffs only. No parallel notifications. |
| **Pattern compression** | Verdict first. Supporting structure after. Templates enforce this at output. |
| **Asymmetric working memory** | Full system view before sequencing. Tables over prose. State externalized in artifacts. |
| **Interest-based activation** | Micro-steps for low-interest tasks. Smallest possible first action. Timed goals. |
| **Executive function offload** | Agents infer and execute. Questions are a last resort. Artifact over discussion. |

**Energy-adaptive routing:**

| Energy | Max Tier | Model Pool | Output |
|--------|----------|------------|--------|
| High | T5 | All 9 | Full execution, all cognitive patterns active |
| Medium | T4 | All 9 | Standard, reduced branching |
| Low | T2 | Gemini + o4-mini | Core task only, 3 bullets max |
| Crash | T1 | None new | "Everything is saved. Nothing is urgent. Come back when ready." |

---

## Loading Order (for LLM context)

When using agents directly (not via the runtime API), load files in this order:

1. [PROFILE.md](PROFILE.md) — cognitive profile and output constraints
2. [models/GEMINI.md](models/GEMINI.md) or [models/OPENAI.md](models/OPENAI.md) — provider-specific instructions
3. [SKILL.md](SKILL.md) — skill invocation protocol
4. [TOOL.md](TOOL.md) — on first tool invocation only

---

## Skill Definitions (audhd-skills)

Skill prompt files are sourced from [AICincy/audhd-skills](https://github.com/AICincy/audhd-skills). The cognitive runtime (`runtime/`) and adapters (`adapters/`) live in this repo only.

---

## Cloud Run Deployment

Infrastructure scaffolding exists in `infra/cloudrun/` and `.github/workflows/deploy-cloud-run.yml`. A Dockerfile is present. **Deployment is not yet validated end-to-end.**

Planned: private authenticated service, Secret Manager for credentials, Workload Identity for GitHub Actions, staging smoke test before production promotion.

See [infra/cloudrun/README.md](infra/cloudrun/README.md) for the full variable and secret reference.

---

## Contributing

Contributions welcome, especially from neurodivergent developers. If you adapt [PROFILE.md](PROFILE.md) to your own cognitive patterns, open a PR — different neurodivergent profiles should be first-class.

Bug reports and skill additions go in [issues](https://github.com/AICincy/audhd-agents/issues).
