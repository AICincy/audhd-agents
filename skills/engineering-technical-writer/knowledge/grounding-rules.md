---
title: Grounding Rules for Technical Writing Claims
domain: technical-writing
subdomain: reality-check
audience: technical writers, AI agents, documentation reviewers
tags: [grounding, reality-check, claims, verification, accuracy, hallucination]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Grounding Rules for Technical Writing Claims

## Purpose

Define rules for grounding technical documentation claims in verifiable evidence. Prevents hallucination, speculation presented as fact, and stale information in AI-generated or human-written documentation. [general]

## Claim Classification

Every factual statement in technical documentation must be classified. [observed]

| Tag | Definition | Evidence Required | Example |
| --- | --- | --- | --- |
| [observed] | Directly retrieved from source code, tool output, or authoritative document | Link to source, commit SHA, or tool output | "The API returns HTTP 429 when rate-limited" [observed] |
| [inferred] | Logically derived from observed facts | State the observed facts and reasoning chain | "Given the 60/min rate limit, batch requests should use 50/min" [inferred] |
| [general] | Widely accepted knowledge in the domain | No citation needed; should be verifiable by any practitioner | "REST APIs use HTTP methods for CRUD operations" [general] |
| [unverified] | Plausible but not verified against current source | Must be explicitly flagged; include verification steps | "The timeout may be configurable via environment variable" [unverified] |

## Grounding Rules

### Rule 1: No Untagged Claims in T3+ Tasks

Every factual statement at task tier T3 or above must carry a claim tag. Untagged claims are treated as violations. [observed]

Exceptions:
- Chat mode (conversational, low-stakes)
- Machine-readable JSON output (no prose claims)
- T1 and T2 tasks (lightweight; tags are optional)

### Rule 2: Source Proximity

Claims must be grounded in the closest authoritative source. [general]

| Priority | Source Type | Example |
| --- | --- | --- |
| 1 | Current source code | Reading the actual implementation |
| 2 | Official documentation | Vendor docs, RFCs, specifications |
| 3 | CI/CD output | Test results, build logs |
| 4 | Domain expertise | General programming knowledge |
| 5 | Community sources | Stack Overflow, blog posts |

Rules:
- Always prefer source code over documentation when they conflict. [general]
- Always prefer official docs over community sources. [general]
- Flag when source code and documentation disagree: this is a documentation bug. [observed]

### Rule 3: Temporal Grounding

Documentation claims have a shelf life. [general]

| Claim Type | Validity Window | Refresh Action |
| --- | --- | --- |
| Version numbers | Until next release | Check on each doc update |
| API endpoints | Until next breaking change | Validate against OpenAPI spec |
| Configuration defaults | Until next config change | Read current config source |
| Performance metrics | 30 days | Re-benchmark |
| Dependency versions | 90 days | Check for updates |
| Architecture descriptions | Until next ADR | Review after each design change |

### Rule 4: Negative Space

Document what is NOT true when it prevents common misconceptions. [general]

Examples:
- "The API does NOT support batch operations" (prevents trial-and-error)
- "This parameter is NOT inherited from the parent configuration" (prevents debugging)
- "Authentication is NOT optional in production; fail-secure is enforced" (prevents security gaps)

### Rule 5: Confidence Calibration

State confidence explicitly when it is not obvious. [general]

| Confidence | When to Use | Phrasing |
| --- | --- | --- |
| High | Verified against current source | "The function returns X" (direct statement) |
| Medium | Inferred from related evidence | "Based on the schema, the function likely returns X" |
| Low | Plausible but unverified | "This may return X; verify against the current implementation" |

### Rule 6: Hallucination Prevention

Specific guards against AI-generated hallucination in documentation. [observed]

| Guard | Implementation |
| --- | --- |
| No invented API endpoints | Every endpoint must exist in the codebase or OpenAPI spec |
| No fabricated error codes | Every error code must be traceable to source |
| No assumed defaults | Every default value must be read from configuration or code |
| No speculative performance claims | Every metric must come from actual benchmarks |
| No fictional examples | Example data must be realistic but clearly synthetic |
| No versionless claims | "Supports X" must specify which version |

### Rule 7: Contradiction Detection

When retrieved context contains contradictory information: [general]

1. Flag the contradiction explicitly in the output.
2. Identify which source is more authoritative (Rule 2: source proximity).
3. Present both claims with their sources.
4. Recommend which to trust and why.
5. File a documentation bug for the incorrect source.

## Reality Check Integration

### Pre-Publication Reality Check

Before any document is published, run these verification steps. [observed]

| Check | Method | Pass Criteria |
| --- | --- | --- |
| Code examples execute | Run in test environment | Exit code 0, output matches |
| API contracts match | Compare against OpenAPI/schema | No field or type mismatches |
| Links resolve | HTTP HEAD on all URLs | All return 200 |
| Version numbers current | Check package registry or release page | Match latest stable |
| Commands work | Execute on target OS | Expected output produced |
| Config values accurate | Read from source/defaults | Match documented values |

### Claim Audit Template

```markdown
## Claim Audit: [Document Title]

| # | Claim | Tag | Source | Verified | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | "API returns 429 at 60 req/min" | [observed] | rate_limiter.py:42 | Yes | Confirmed |
| 2 | "Default timeout is 30s" | [observed] | config.yaml:15 | Yes | Confirmed |
| 3 | "Supports PostgreSQL 14+" | [unverified] | README.md | No | README says 15+ |
| 4 | "Horizontal scaling to 50 replicas" | [inferred] | HPA config | Yes | Max set to 50 |
```

### Automated Grounding Checks

Integrate these checks into CI/CD for documentation. [general]

| Check | Tool | Automation Level |
| --- | --- | --- |
| Link checking | linkchecker, markdown-link-check | Fully automated |
| Code example testing | mdx-test, pytest-markdown | Fully automated |
| Spell checking | cspell, hunspell | Fully automated |
| Readability scoring | readability-score | Fully automated |
| API contract validation | openapi-diff, schemathesis | Fully automated |
| Claim tag presence | Custom linter (regex) | Fully automated |
| Factual accuracy | Human review + AI assist | Semi-automated |

## RAG-Specific Grounding Rules

When generating documentation using retrieved context (RAG): [observed]

1. All claims derived from retrieved sources must be tagged [observed].
2. If retrieved context is insufficient, state so explicitly; do not fabricate content.
3. If retrieved context is contradictory, follow Rule 7 (contradiction detection).
4. LOW energy: process maximum 3 retrieved chunks.
5. CRASH energy: no RAG processing; defer to human writer.
6. Include source attribution: "According to [source], ..." for key claims.
7. Distinguish between what the retrieved context says and what you infer from it.

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| "I believe the API supports..." | Belief is not evidence | Verify against source; tag appropriately |
| Presenting defaults without checking | Defaults change between versions | Read from current source code or config |
| Citing blog posts as authoritative | Blog posts are opinions, not specs | Cite official docs or source code |
| "Works on my machine" | Not reproducible | Test in clean environment |
| Stale screenshots | UI changes faster than docs | Describe actions in text; screenshots supplement |
| Confident tone on uncertain claims | Misleads the reader | Calibrate confidence (Rule 5) |

## Grounding Checklist

Before publishing any documentation, verify: [observed]
- [ ] Every factual claim is tagged ([observed], [inferred], [general], [unverified])
- [ ] [observed] claims link to a verifiable source
- [ ] [unverified] claims include suggested verification steps
- [ ] Code examples have been executed and output verified
- [ ] No invented endpoints, error codes, or configuration values
- [ ] Version numbers and dependencies are current
- [ ] Contradictions between sources are flagged and resolved
- [ ] Confidence is calibrated: strong claims have strong evidence
