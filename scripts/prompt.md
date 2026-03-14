# Diagnostic Scripts

## Goal

Validate system configuration, provider connectivity, and runtime health. Surface actionable failures with concrete remediation steps. Two modes: config (structure only, no API calls) and live (real provider requests).

## Rules

- Config mode: validate repo structure, alias resolution, skill loading. No API calls, no credentials required.
- Live mode: all config checks plus real requests to each required provider. Requires .env with valid API keys.
- Classify every error into concrete operator guidance: what broke, why, how to fix.
- Report pass/fail for each check. Failures first, passes second.
- Exit code 0 on full pass, 1 on any failure.
- No em dashes

## Workflow

1. **Environment**: Check .env presence, load RuntimeSettings, report required providers
2. **Router Init**: Initialize SkillRouter from adapters/config.yaml. Fail fast if config is malformed.
3. **Provider Status**: For each provider: key presence, model list, circuit breaker state. In live mode, verify key is accepted by API.
4. **Instruction Stack**: Verify PROFILE.md, SKILL.md, TOOL.md, and all model-specific files exist and are non-empty.
5. **Alias Resolution**: For each alias in alias_map, resolve to provider/model tuple. Flag invalid targets.
6. **Skill Inventory**: Walk skills/ directory, load every skill.yaml. Report count by category. Flag load failures.
7. **Live Validation** (live mode only): Send minimal prompt to each required provider. Classify errors (auth, model not found, rate limit, permission denied).
8. **Report**: Aggregate all results. Print structured output. Return exit code.

## Output

Structured diagnostic report with pass/fail per check, error classification, and operator remediation guidance.
