# Build and Diagnostics Prompt

## Goal

Execute build and diagnostic scripts for the audhd-agents system. Generate dist/ manifests from skill definitions and validate provider connections.

## Rules

1. `build.py` reads all `skills/*/skill.yaml` files and generates provider-specific manifests in `dist/`.
2. `check_connections.py --mode config` validates configuration without making API calls.
3. `check_connections.py --mode live` tests actual provider connectivity (use as release gate).
4. Never run live checks in CI without explicit approval (costs money, may rate limit).
5. Build failures must report which skill definition failed validation and why.

## Workflow

### Build

1. Scan `skills/` directory for all `skill.yaml` files.
2. Validate each against schema.
3. Generate provider-specific manifests (Anthropic, OpenAI, Google).
4. Write to `dist/` directory.
5. Report: skills processed, manifests generated, any validation errors.

### Diagnostics

1. Load `adapters/config.yaml` for provider configuration.
2. Config mode: validate structure, required fields, API key presence.
3. Live mode: make test API call to each configured provider.
4. Report: provider status table (provider, status, latency, error).

## Output

- Build: count of skills processed, manifests written, errors.
- Diagnostics: provider status table (provider, status, latency, error).
