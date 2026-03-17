# AGENT.md: Swarm Orchestration Protocol

Reference document for Operator. Defines topology, routing, escalation, and inter-agent contracts.

---

## Topology

Hub-and-spoke with orchestrator-managed autonomous handoffs. Operator remains the control surface.

- Autonomous handoffs are allowed when routing is pre-authorized by the active workflow or routing matrix.
- Every handoff must carry explicit state: goal, constraints, partial results, evidence, and next action.
- No opaque peer-to-peer state changes outside orchestrator-managed routing.
- Exception: Codex may be sub-invoked for inline code generation within pre-authorized workflows.
- Rationale: monotropic attention requires single-thread visibility, not manual relay. Handoffs should feel seamless while state remains explicit.

---

## Agent Registry

| ID | Model | Role | Primary Domain |
| --- | --- | --- | --- |
| G-PRO | Gemini 2.5 Pro | Deep Analyst / Integrator | Complex analysis, OSINT, research, multimodal |
| G-PRO31 | Gemini 3.1 Pro Preview | Deep Analyst / Integrator | Complex analysis, drafting, OSINT, high-tier |
| G-FLA31 | Gemini 3.1 Flash | Rapid Verifier / Analyst | Fast analysis, triage, quick drafts |
| O-54P | GPT-5.4 Pro | Deep Planner / Analyst | Architecture, audit synthesis, escalation review |
| O-54 | GPT-5.4 | Ideation Engine (Primary) | Creative, stakeholder comms, accessibility review |
| O-53 | GPT-5.3 | Ideation Engine (Fallback) | Same scope as O-54 |
| O-CDX | GPT-5.3 Codex | Code Automator | Scripts, pipelines, automation, environment scaffolding |
| O-O4M | o4-mini | Rapid Verifier | Benchmarks, triage, structured checks, numeric sanity checks |

---

## Routing Matrix

| Domain | T1-T2 | T3 | T4-T5 | Fallback |
| --- | --- | --- | --- | --- |
| Analysis | G-FLA31 | G-PRO31 | G-PRO31 | G-PRO then O-54P |
| Code | O-CDX | O-CDX | O-CDX + G-PRO review | O-54 |
| Research | G-PRO | G-PRO | G-PRO + O-54P verify | O-54 |
| Drafting (internal) | G-FLA31 | G-PRO31 | G-PRO31 | G-PRO then O-54 |
| Drafting (final) | G-FLA31 | G-PRO31 | G-PRO31 + O-54 review | G-PRO then O-53 |
| OSINT | n/a | G-PRO31 | G-PRO31 + O-54P | G-PRO then O-54 |
| Stakeholder comms | G-PRO | G-PRO | G-PRO + O-54 verify | O-54 |
| Creative | G-PRO | G-PRO | G-PRO | O-54 |
| Triage | G-FLA31 | n/a | n/a | G-PRO |

Fallback activates on: API error, rate limit, or explicit agent deferral.

---

## Circuit Breakers

Automatic protection against cascading failures and degraded service.

| Breaker | Trigger | Action | Reset Condition |
| --- | --- | --- | --- |
| Error spike | 3+ consecutive failures from same adapter | Route all traffic to fallback. Log failure pattern. | Primary model returns 3 consecutive successes |

One circuit breaker instance exists per adapter (see `adapters/base.py`).

---

## Cost Tracking

Every model interaction should be cost-aware.

| Model | Tier | Relative Cost | When to Prefer |
| --- | --- | --- | --- |
| O-O4M | Budget | $ | Benchmarks, scorecards, structured validation, fast quantitative checks |
| G-FLA31 | Budget | $ | Triage, fast drafts, standard analysis |
| G-PRO | Mid | $$ | Research, search grounding, multimodal, deep analysis |
| G-PRO31 | Mid | $$ | High-tier analysis, drafting, OSINT |
| O-54 / O-53 | Mid | $$ | Creative, stakeholder comms, ideation, accessibility review |
| O-CDX | Mid | $$ | Code generation, scripting, automation |
| O-54P | Premium | $$$ | Architecture, audit synthesis, planning, escalations, T5 verification |

**Rule:** Always prefer the cheapest model that meets the tier requirement. Do not route T1 tasks to Premium models.

**Rule:** When proposing multi-model workflows, include estimated relative cost (low/medium/high).

> CostRecord exists in `adapters/base.py` but is not yet wired to routing decisions.

---

## Incident Severity Classification

| Severity | Definition | Response Time | Escalation |
| --- | --- | --- | --- |
| SEV1: Critical | Data loss, security breach, production outage, wrong output sent externally | Immediate | Halt all work. Alert Operator. Full incident report. |
| SEV2: High | Blocked workflow, incorrect output caught before delivery, repeated model failures | Within current session | Fallback model + flag for Operator review |
| SEV3: Medium | Degraded quality, slow responses, minor inaccuracies in non-critical output | Next available cycle | Log and fix. No immediate escalation. |
| SEV4: Low | Style issues, suboptimal routing, minor tool errors that self-resolved | Batch with next update | Log only |

---

## Task Classification (T1-T5)

| Tier | Complexity | Verification |
| --- | --- | --- |
| T1 Trivial | Status check, yes/no, format conversion | None |
| T2 Standard | Summarize, template, simple fix, short draft | None |
| T3 Complex | Multi-step analysis, code module, research synthesis | Optional |
| T4 Expert | Legal IRAC, multi-entity OSINT, architecture | Recommended |
| T5 Critical | Final filings, production deploys, public docs | Mandatory dual-model |

---

## Authentication

API endpoints (`/execute`) are protected by Bearer token auth via `Depends(verify_api_key)`. Tokens are configured through the `AUDHD_API_KEYS` environment variable. When no keys are configured, the service returns 503 (fail-secure).

---

## Energy-Adaptive Routing

| Energy | Max Tier | Model Pool | Behavior |
| --- | --- | --- | --- |
| High | T5 | All 8 | Normal operation |
| Medium | T4 | All 8, prefer fast models for T1-T2 | Standard |
| Low | T2 | Gemini + o4-mini only | Micro-steps. Single next action. |
| Crash | T1 | None new | "Everything is saved. Nothing is urgent. Come back when ready." |

No tasks lost during downgrade. Deferred items queue for next high-energy window.

---

## Handoff Format

```text
HANDOFF
  FROM: [completing model]
  TO: [receiving model]
  TASK_ID: [unique identifier]
  CONTEXT: [3 sentences max]
  ARTIFACTS: [list of outputs]
  CONSTRAINTS: [inherited]
  SUCCESS_TEST: [done criteria]
```

### Handoff Rules

1. Operator or the orchestrator may initiate handoffs when routing is pre-authorized
2. Receiving agent loads PROFILE.md before processing
3. Receiving agent acknowledges constraints before output
4. No agent modifies another agent's artifacts without approval
5. State externalized in artifacts, never assumed from memory

> Handoff format is defined but not code-enforced at runtime.

---

## Inter-Agent Contracts (AuDHD Architectural Constraints)

| Contract | Specification |
| --- | --- |
| One active thread | System presents exactly one result at a time. No parallel notifications. |
| No unsolicited decisions | Never present "Would you like to..." prompts. Infer or defer. |
| Predictable structure | Every result follows same template: summary, details, next step. |
| Where Was I? | On return after 30+ min absence, auto-present last context with single-action resume. |
| Crash mode protection | During crash energy: confirm state is saved, do nothing else. |

---

## Planned / Not Yet Implemented

The following features are defined in contracts or documentation but are not yet code-enforced:

- [planned] **Cost-aware routing**: CostRecord exists but is not wired to model selection logic.
- [planned] **Confidence thresholds**: No confidence scoring exists in the router.
- [planned] **Escalation protocol**: No human-escalation path is implemented.
- [planned] **Multi-circuit-breaker topology**: Only a single error-spike breaker per adapter exists. Cost ceiling, rate-limit-cascade, and anomaly detector breakers are aspirational.
