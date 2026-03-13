# AUDHD Cognitive Swarm Protocol

Multi-agent orchestration system designed for AuDHD cognition. Hub-and-spoke topology with 9 models, skill-based cognitive augmentation, and LLM-specific deployment adapters.

Built by and for neurodivergent engineers who need AI systems that work *with* their cognitive architecture instead of against it.

## Architecture

```
audhd-agents/
├── KRASS.md                    # Cognitive profile + universal constraints
├── AGENT.md                    # Swarm orchestration + routing matrix
├── TOOL.md                     # Tool contracts + error classification
├── SKILL.md                    # Cognitive support skills (SK-*)
├── models/
│   ├── CLAUDE.md               # Claude Opus/Sonnet instructions
│   ├── GEMINI.md               # Gemini Pro instructions
│   └── OPENAI.md               # ChatGPT/Codex/Max instructions
├── capabilities/               # Atomic capability definitions (Beta Pro)
├── skills/                     # AIO canonical skill definitions
│   └── {skill-name}/
│       ├── skill.yaml          # Canonical definition
│       ├── prompt.md           # Prompt logic
│       ├── schema.json         # Function schema
│       └── examples.json       # Test invocations
├── graphs/                     # Capability chaining (Beta Pro)
├── agents/                     # Agent compositions (Beta Pro)
├── adapters/
│   ├── config.yaml             # Provider config + model routing
│   ├── router.py               # Skill-to-model router with failover
│   ├── anthropic_adapter.py    # Claude adapter
│   ├── openai_adapter.py       # OpenAI adapter
│   └── google_adapter.py       # Gemini adapter
├── runtime/                    # Router, planner, executor (Beta Pro)
├── dist/                       # Generated per-LLM manifests
├── .vscode/                    # VS Code configuration
└── build.py                    # Master build script
```

## Models (9)

| ID | Model | Role |
|---|---|---|
| C-OP46 | Claude Opus 4.6 | Deep Analyst (Primary) |
| C-OP45 | Claude Opus 4.5 | Deep Analyst (Fallback) |
| C-SN46 | Claude Sonnet 4.6 | Rapid Executor (Primary) |
| C-SN45 | Claude Sonnet 4.5 | Rapid Executor (Fallback) |
| G-PRO | Gemini 3.1 Pro (Preview) | Knowledge Integrator |
| O-54 | ChatGPT 5.4 | Ideation Engine (Primary) |
| O-53 | ChatGPT 5.3 | Ideation Engine (Fallback) |
| O-CDX | Codex | Code Automator |
| O-MAX | Max | Generalist Overflow |

## Cognitive Design Principles

This system is built around AuDHD cognitive patterns:

- **Monotropism:** Single-thread control. No autonomous agent-to-agent chatter.
- **Pattern compression:** Verdict first, supporting structure second.
- **Asymmetric working memory:** Maps over turn-by-turn. Full system view before sequencing.
- **Interest-based activation:** Micro-sprints, momentum tracking, smallest-possible first actions.
- **Executive function offload:** Agents infer and execute. Questions are a last resort.

## Skill System (AIO)

Each skill is a canonical definition that builds to all 3 LLM formats:

- **skill.yaml**: Name, description, capabilities, inputs, outputs, model mappings
- **prompt.md**: Prompt logic with goal, rules, workflow, output format
- **schema.json**: Function/tool schema for input validation
- **examples.json**: Test invocations for validation

51 skills across engineering, design, testing, project management, marketing, and specialized domains.

Run `python build.py` to generate `dist/` manifests for each LLM.

## Setup

1. Clone this repo
2. Open in VS Code (recommended extensions auto-suggested)
3. `cp .env.example .env` and fill in your API keys
4. `pip install -r requirements.txt`
5. `python build.py` to generate LLM-specific files in `dist/`
6. Deploy generated manifests to respective platforms

## Loading Order (All Models)

1. `KRASS.md` (cognitive profile, universal constraints)
2. Model-specific file (`models/CLAUDE.md`, `models/GEMINI.md`, or `models/OPENAI.md`)
3. `SKILL.md` (cognitive support skills)
4. `TOOL.md` (on first tool invocation)

## Contributing

Contributions welcome, especially from neurodivergent developers. The cognitive profile in KRASS.md can be forked and adapted to your own patterns.

## License

MIT. See [LICENSE](LICENSE).
