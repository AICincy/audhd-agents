---
title: Documentation Review Checklist
domain: technical-writing
subdomain: quality-assurance
audience: documentation reviewers, technical writers, editors
tags: [review, checklist, quality, accuracy, completeness, readability]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Documentation Review Checklist

## Purpose

Provide a structured review framework for evaluating technical documentation quality. Each dimension has specific, measurable criteria. [general]

## Review Dimensions

| Dimension | Weight | Focus |
| --- | --- | --- |
| Accuracy | Critical | Factual correctness, code examples work |
| Completeness | High | All required sections present, no gaps |
| Clarity | High | Readability, scannability, comprehension |
| Structure | Medium | Logical organization, progressive disclosure |
| Style | Medium | Consistency with style guide |
| Accessibility | Medium | WCAG compliance, inclusive language |
| Maintainability | Low | Ease of future updates, no hard-coded values |

## Accuracy Review

### Code Accuracy

| Check | Criteria | Severity |
| --- | --- | --- |
| Code compiles/runs | Every code example executes without errors | Critical |
| Output matches | Shown output matches actual execution output | Critical |
| Versions correct | Language, library, and tool versions are current | High |
| Commands work | CLI commands work on stated OS and environment | Critical |
| Links resolve | All URLs return 200 (not 404 or redirect loops) | High |

### Technical Accuracy

| Check | Criteria | Severity |
| --- | --- | --- |
| API contracts match | Documented parameters match actual API | Critical |
| Behavior described correctly | Documented behavior matches implementation | Critical |
| Error codes complete | All possible errors are documented | High |
| Default values correct | Documented defaults match code defaults | High |
| Constraints accurate | Documented limits match actual limits | High |

### Claim Grounding

| Check | Criteria | Severity |
| --- | --- | --- |
| Claims tagged | All factual claims have [observed], [inferred], [general], or [unverified] | Medium |
| Sources cited | [observed] claims link to source evidence | High |
| Speculation flagged | Uncertain claims marked [unverified] | High |
| No unsupported absolutes | "Always", "never", "all" backed by evidence | Medium |

## Completeness Review

### Required Sections by Document Type

| Document Type | Required Sections |
| --- | --- |
| API Reference | Summary, Auth, Request, Response, Errors, Examples |
| Tutorial | Outcomes, Prerequisites, Steps, Verification, Summary, Next Steps |
| How-To | Goal, Prerequisites, Steps, Verification, Troubleshooting |
| Architecture | Context diagram, Components, Decisions, Invariants, NFRs |
| Runbook | Alert details, Diagnosis, Resolution, Verification, Escalation |
| README | Description, Quickstart, Usage, Architecture link, License |

### Content Completeness

| Check | Criteria |
| --- | --- |
| Prerequisites listed | All dependencies, versions, prior setup |
| Happy path documented | Main workflow from start to finish |
| Error paths documented | What happens when things go wrong |
| Edge cases covered | Boundary conditions, empty states, large inputs |
| Next steps provided | Where to go after this document |

## Clarity Review

### Readability Metrics

| Metric | Target | Tool |
| --- | --- | --- |
| Flesch-Kincaid Grade Level | 8 to 10 for tutorials, 10 to 12 for reference | readability-score |
| Average sentence length | Under 25 words | Manual count or linter |
| Paragraph length | Under 4 sentences | Manual count |
| Heading density | One heading per 200 to 300 words | Word count |

### Scannability Checks

| Check | Criteria |
| --- | --- |
| Headings as navigation | Reader can find any section by scanning headings |
| Lists for sequences | Ordered steps use numbered lists |
| Tables for comparisons | Side-by-side data uses tables, not paragraphs |
| Code blocks highlighted | Syntax highlighting with correct language tag |
| Key terms bold or code-formatted | Important terms visually distinct |

### Comprehension Checks

| Check | Criteria |
| --- | --- |
| Jargon defined | Every technical term defined on first use |
| Acronyms expanded | Spelled out on first use with abbreviation in parentheses |
| Context before action | One sentence explaining "why" before each "how" |
| One idea per paragraph | No paragraph covers multiple concepts |
| No assumed knowledge | Everything needed is stated or linked |

## Structure Review

### Organization Checks

| Check | Criteria |
| --- | --- |
| Logical flow | Sections build on previous sections |
| Progressive disclosure | Simple concepts before complex ones |
| Heading hierarchy | No skipped levels (H2 then H4) |
| Consistent patterns | Similar content types structured the same way |
| Cross-references | Related documents linked where relevant |

### Navigation Checks

| Check | Criteria |
| --- | --- |
| Table of contents | Present for documents over 1000 words |
| Anchor links work | All internal links resolve to correct sections |
| Breadcrumbs | Reader knows where they are in the doc hierarchy |
| Back/next links | Sequential content has navigation between pages |

## Style Review

### Language Checks

| Check | Criteria |
| --- | --- |
| Active voice | Subject performs action (>80% of sentences) |
| Present tense | "Returns" not "will return" |
| Imperative for instructions | "Run the command" not "You should run the command" |
| No filler words | No "simply", "easily", "just", "obviously" |
| No em dashes | Colons, semicolons, or parentheses instead |
| No exclamation marks | Neutral, professional tone |

### Consistency Checks

| Check | Criteria |
| --- | --- |
| Terminology | Same term used throughout (not alternating synonyms) |
| Formatting | Code, paths, UI elements formatted consistently |
| Capitalization | Sentence case for headings, consistent for terms |
| Date format | ISO 8601 or stated format used consistently |
| Number format | Consistent use of numerals vs. words |

## Accessibility Review

### Content Accessibility

| Check | Criteria | WCAG |
| --- | --- | --- |
| Alt text on images | Descriptive, not decorative | 1.1.1 |
| Heading hierarchy | Proper nesting for screen readers | 1.3.1 |
| Descriptive links | No "click here" or "read more" alone | 2.4.4 |
| Color independence | Meaning not conveyed by color alone | 1.4.1 |
| Text contrast | 4.5:1 ratio minimum in embedded content | 1.4.3 |
| Language attribute | Document language declared | 3.1.1 |

### Inclusive Language

| Check | Criteria |
| --- | --- |
| No exclusionary terms | No whitelist/blacklist, master/slave |
| Gender-neutral | "They" for unknown gender, "developer" not "he" |
| Cultural sensitivity | No idioms that may not translate |
| Reading level appropriate | Matches stated audience |

## Maintainability Review

| Check | Criteria |
| --- | --- |
| No hard-coded values | Use variables or references for URLs, versions, dates |
| Version-independent where possible | Instructions work across minor versions |
| Modular structure | Sections reusable across documents |
| Source in version control | Documentation stored alongside code |
| Review history | Changes tracked via git, not inline annotations |

## Review Severity Scale

| Severity | Definition | Action |
| --- | --- | --- |
| Critical | Blocks user success (wrong command, broken example) | Must fix before publish |
| High | Significant gap or confusion risk | Fix in current review cycle |
| Medium | Style violation or minor gap | Fix within one week |
| Low | Enhancement opportunity | Add to backlog |

## Review Output Template

```markdown
## Documentation Review: [Document Title]

### Summary
- **Reviewer**: [Name]
- **Date**: [ISO 8601 date]
- **Verdict**: [Approve | Revise | Reject]
- **Critical issues**: [count]
- **High issues**: [count]

### Findings

| # | Severity | Dimension | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- | --- |
| 1 | Critical | Accuracy | Section 3, code block | Command fails on macOS | Update flag to -f |
| 2 | High | Completeness | Auth section | Missing OAuth2 flow | Add token refresh docs |
| 3 | Medium | Style | Throughout | Passive voice in 40% | Rewrite to active voice |

### Next Action
[Single most important action to take before re-review.]
```

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| Reviewing only for grammar | Misses accuracy and completeness issues | Use all seven review dimensions |
| Approving without testing code | Broken examples ship to users | Execute every code block in a test environment |
| Review without severity ranking | All issues appear equally important | Assign Critical, High, Medium, Low to each finding |
| Single-pass review | Later sections get less attention | Review each dimension separately in focused passes |
| Reviewing your own work alone | Author blindness misses gaps and assumptions | Include at least one reviewer who did not write the document |

## Grounding Checklist

This checklist is the meta-checklist: verify the review itself is thorough. [observed]
- [ ] All seven review dimensions evaluated
- [ ] Code examples tested (not just read)
- [ ] Links checked for liveness
- [ ] Severity assigned to every finding
- [ ] Findings include specific location and recommendation
- [ ] Review verdict is clear (Approve, Revise, Reject)
- [ ] Single next action identified
