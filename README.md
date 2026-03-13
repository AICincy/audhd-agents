# AUDHD Cognitive Swarm Protocol

Multi-agent orchestration system for AuDHD cognition. Hub-and-spoke topology with 9 models, skill-based cognitive augmentation, and LLM-specific deployment adapters.

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
│   ├── openai/                 # ChatGPT adapter
│   ├── anthropic/              # Claude adapter
│   └── gemini/                 # Gemini adapter
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

## Skill System (AIO)

Each skill is a canonical definition that builds to all 3 LLM formats:

- **skill.yaml**: Name, description, capabilities, inputs, outputs, model mappings
- **prompt.md**: Prompt logic with goal, rules, workflow, output format
- **schema.json**: Function/tool schema for input validation
- **examples.json**: Test invocations for validation

Run `python build.py` to generate `dist/` manifests for each LLM.

## Setup

1. Clone this repo
2. Open in VS Code (recommended extensions auto-suggested)
3. `pip install -r requirements.txt`
4. `python build.py` to generate LLM-specific files in `dist/`
5. Deploy generated manifests to respective platforms

## Loading Order (All Models)

1. `KRASS.md` (cognitive profile, universal constraints)
2. Model-specific file (`models/CLAUDE.md`, `models/GEMINI.md`, or `models/OPENAI.md`)
3. `SKILL.md` (cognitive support skills)
4. `TOOL.md` (on first tool invocation)

## License

Private. All rights reserved.
