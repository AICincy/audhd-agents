# AGENT.md: Swarm Orchestration Protocol

Reference document for Operator. Defines topology, routing, escalation, and inter-agent contracts.

---

## Topology

Hub-and-spoke. Operator is the hub.

- No autonomous agent-to-agent communication.
- All routing flows through Operator explicitly.
- Exception: Codex may be sub-invoked for inline code generation within pre-authorized workflows.
- Rationale: monotropic attention requires single-thread control. Autonomous handoffs create invisible state changes.

---

## Agent Registry

| ID | Model | Role | Primary Domain |
|---|---|---|---|
| C-OP46 | Claude Opus 4.6 | Deep Analyst (Primary) | Complex analysis, OSINT, legal, architecture, T5 verification |
| C-OP45 | Claude Opus 4.5 | Deep Analyst (Fallback) | Same scope as C-OP46 |
| C-SN46 | Claude Sonnet 4.6 | Rapid Executor (Primary) | Structured output, triage, drafts, reformatting |
| C-SN45 | Claude Sonnet 4.5 | Rapid Executor (Fallback) | Same scope as C-SN46 |
| G-PRO | Gemini 3.1 Pro (Preview) | Knowledge Integrator | Research, multimodal, Google ecosystem, search grounding |
| O-54 | ChatGPT 5.4 | Ideation Engine (Primary) | Creative, stakeholder comms, accessibility review |
| O-53 | ChatGPT 5.3 | Ideation Engine (Fallback) | Same scope as O-54 |
| O-CDX | Codex | Code Automator | Scripts, pipelines, automation, environment scaffolding |
| O-MAX | Max | Generalist Overflow | Parallel capacity, second opinions, bulk processing |

---

## Routing Matrix

| Domain | T1-T2 | T3 | T4-T5 | Fallback |
|---|---|---|---|---|
| Analysis | C-SN46 | C-OP46 | C-OP46 | C-OP45 then C-SN45 |
| Code | O-CDX | O-CDX | O-CDX + C-OP46 review | O-54 |
| Research | G-PRO | G-PRO | G-PRO + C-OP46 verify | C-OP45 |
| Drafting (internal) | C-SN46 | C-SN46 | C-OP46 | C-SN45 |
| Drafting (final) | C-OP46 | C-OP46 | C-OP46 + O-54 review | C-OP45 |
| OSINT | n/a | C-OP46 | C-OP46 + G-PRO | C-OP45 |
| Stakeholder comms | O-54 | O-54 | O-54 + C-OP46 verify | O-53 |
| Creative | O-54 | O-54 | O-54 | O-53 |
| Triage | C-SN46 | n/a | n/a | C-SN45 |
| Overflow | O-MAX | O-MAX | O-MAX | O-53 |

Fallback activates on: API error, rate limit, confidence below 0.6, or explicit agent deferral.

---

## Circuit Breakers

Automatic protection against runaway costs, cascading failures, and degraded service.

| Breaker | Trigger | Action | Reset Condition |
|---|---|---|---|
| Cost ceiling | Estimated session cost exceeds threshold (set per task) | Halt new API calls. Present cost report to Operator. | Operator approves budget increase |
| Error spike | 3+ consecutive failures from same model in 5 min | Route all traffic to fallback. Log failure pattern. | Primary model returns 3 consecutive successes |
| Rate limit cascade | 2+ models rate-limited simultaneously | Queue non-urgent tasks. Process only T4-T5. | Any 2 models return to normal availability |
| Anomaly detector | 500% traffic spike or repeated HTTP 402/429 | Immediately halt all automated calls. Alert Operator. | Manual Operator review |

---

## Cost Tracking

Every model interaction should be cost-aware.

| Model | Tier | Relative Cost | When to Prefer |
|---|---|---|---|
| C-SN46 / C-SN45 | Budget | $ | T1-T2, triage, formatting, quick drafts |
| G-PRO | Mid | $$ | Research, search grounding, multimodal |
| O-54 / O-53 / O-MAX | Mid | $$ | Creative, stakeholder comms, overflow |
| O-CDX | Mid | $$ | Code generation, scripting, automation |
| C-OP46 / C-OP45 | Premium | $$$ | T3+ analysis, OSINT, architecture, verification |

**Rule:** Always prefer the cheapest model that meets the tier requirement. Do not route T1 tasks to Opus.

**Rule:** When proposing multi-model workflows, include estimated relative cost (low/medium/high).

---

## Incident Severity Classification

| Severity | Definition | Response Time | Escalation |
|---|---|---|---|
| SEV1: Critical | Data loss, security breach, production outage, wrong output sent externally | Immediate | Halt all work. Alert Operator. Full incident report. |
| SEV2: High | Blocked workflow, incorrect output caught before delivery, repeated model failures | Within current session | Fallback model + flag for Operator review |
| SEV3: Medium | Degraded quality, slow responses, minor inaccuracies in non-critical output | Next available cycle | Log and fix. No immediate escalation. |
| SEV4: Low | Style issues, suboptimal routing, minor tool errors that self-resolved | Batch with next update | Log only |

---

## Task Classification (T1-T5)

| Tier | Complexity | Verification |
|---|---|---|
| T1 Trivial | Status check, yes/no, format conversion | None |
| T2 Standard | Summarize, template, simple fix, short draft | None |
| T3 Complex | Multi-step analysis, code module, research synthesis | Optional |
| T4 Expert | Legal IRAC, multi-entity OSINT, architecture | Recommended |
| T5 Critical | Final filings, production deploys, public docs | Mandatory dual-model |

---

## Escalation Protocol

| Level | Trigger | Action |
|---|---|---|
| 1 | Confidence below 0.6 or transient error | Retry same model, max 3 attempts |
| 2 | 3 failed retries or capability gap | Route to fallback agent per matrix |
| 3 | Fallback also fails or conflicting results | Multi-model consensus: C-OP46 + G-PRO + O-54 |
| 4 | Consensus unresolved or human judgment required | Queue for Operator review (single-item presentation) |

---

## Energy-Adaptive Routing

| Energy | Max Tier | Model Pool | Behavior |
|---|---|---|---|
| High | T5 | All 9 | Normal operation |
| Medium | T4 | All 9, prefer fast models for T1-T2 | Standard |
| Low | T2 | Sonnet + Gemini only | Micro-steps. Single next action. |
| Crash | T1 | None new | "Everything is saved. Nothing is urgent. Come back when ready." |

No tasks lost during downgrade. Deferred items queue for next high-energy window.

---

## Handoff Format

```
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

1. Operator initiates all handoffs explicitly
2. Receiving agent loads PROFILE.md before processing
3. Receiving agent acknowledges constraints before output
4. No agent modifies another agent's artifacts without approval
5. State externalized in artifacts, never assumed from memory

---

## Inter-Agent Contracts (AuDHD Architectural Constraints)

| Contract | Specification |
|---|---|
| One active thread | System presents exactly one result at a time. No parallel notifications. |
| No unsolicited decisions | Never present "Would you like to..." prompts. Infer or defer. |
| Predictable structure | Every result follows same template: summary, details, next step. |
| Where Was I? | On return after 30+ min absence, auto-present last context with single-action resume. |
| Crash mode protection | During crash energy: confirm state is saved, do nothing else. |
