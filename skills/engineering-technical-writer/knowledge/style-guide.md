---
title: Technical Writing Style Guide
domain: technical-writing
subdomain: style
audience: technical writers, developers, documentation reviewers
tags: [style, formatting, tone, voice, grammar, accessibility]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Technical Writing Style Guide

## Purpose

Define consistent voice, tone, formatting, and language rules for technical documentation. Style consistency builds trust and reduces cognitive load. [general]

## Voice and Tone

### Voice Principles

| Principle | Description | Example |
| --- | --- | --- |
| Direct | State the action; do not suggest it | "Run the migration" not "You might want to run the migration" |
| Precise | Use exact terms; avoid vague language | "Returns HTTP 404" not "Returns an error" |
| Respectful | Assume competence; do not condescend | "Configure the proxy" not "Simply configure the proxy" |
| Scannable | Structure for quick navigation | Use headings, tables, and lists |

### Words to Avoid

| Avoid | Reason | Use Instead |
| --- | --- | --- |
| Simply, easily, just | Dismisses difficulty; condescending | Remove the word entirely |
| Obviously, clearly | Implies the reader should already know | State the fact directly |
| Please | Unnecessary politeness in instructions | Use imperative: "Run", "Open", "Create" |
| Note that | Filler; adds no information | State the note directly |
| In order to | Verbose | "To" |
| Utilize | Formal jargon | "Use" |
| Leverage | Business jargon in technical context | "Use" |
| A number of | Vague | State the actual number |
| Etc. | Vague; reader does not know what is omitted | List all items or say "and others" |

### Punctuation Rules

| Rule | Guideline |
| --- | --- |
| Em dashes | Never use em dashes or en dashes. Use colons, semicolons, or parentheses. [observed] |
| Oxford comma | Always use the Oxford comma in lists. [general] |
| Periods in lists | Use periods for complete sentences. Omit for fragments. [general] |
| Exclamation marks | Never in technical documentation. [general] |
| Semicolons | Use to join related independent clauses. [general] |

## Formatting Standards

### Headings

1. Use headings as navigation anchors. Readers scan headings before reading content. [general]
2. Use sentence case: "Configure the database", not "Configure The Database". [general]
3. Maximum heading depth: H4. Deeper nesting indicates the page should be split. [observed]
4. Headings must be unique within a page (for anchor link reliability). [general]
5. Do not skip heading levels: H2 then H4 is incorrect. [general]

### Lists

| List Type | When to Use |
| --- | --- |
| Numbered | Steps where order matters |
| Bulleted | Items where order does not matter |
| Definition | Term and description pairs |

Rules: [general]
- Parallel structure: all items start with the same part of speech.
- Maximum 7 items before grouping into sub-lists or tables.
- One idea per list item.

### Tables

Use tables instead of paragraphs for comparisons, mappings, and structured data. [observed]

| Guideline | Detail |
| --- | --- |
| Column headers | Always present, descriptive |
| Alignment | Left-align text, right-align numbers |
| Cell content | Brief; link to details if needed |
| Row count | Under 20; paginate or group if larger |

### Code Formatting

| Element | Format |
| --- | --- |
| Inline code | Backticks: `variable_name`, `kubectl get pods` |
| Code blocks | Fenced with language identifier: ```python |
| File paths | Backticks: `src/runtime/hooks.py` |
| UI elements | Bold: **Save**, **Settings** |
| Keyboard shortcuts | Kbd format: `Ctrl+C` |
| Placeholders | Angle brackets: `<your-api-key>` |

## Sentence and Paragraph Rules

1. Maximum sentence length: 25 words. Split longer sentences. [general]
2. Maximum paragraph length: 4 sentences. Break at logical boundaries. [general]
3. One idea per paragraph. [general]
4. Active voice: "The server returns a 200 status" not "A 200 status is returned by the server". [general]
5. Present tense: "The function validates input" not "The function will validate input". [general]
6. Second person for instructions: "You configure" or imperative "Configure". [general]

## Terminology Consistency

### Glossary Rules

1. Define every term on first use. [general]
2. Use one term consistently: choose "endpoint" or "route", not both. [general]
3. Maintain a project glossary for domain-specific terms. [general]
4. Abbreviations: spell out on first use, abbreviation in parentheses. "Service Level Objective (SLO)". [general]

### Technical Term Standards

| Term | Use | Do Not Use |
| --- | --- | --- |
| Repository | When referring to version control | Repo (in formal docs) |
| API | Spell out on first use: Application Programming Interface | Spell out every time |
| URL | No need to spell out (universally known) | Uniform Resource Locator |
| Boolean | Capitalize (proper noun: George Boole) | boolean |
| ID | All caps | Id, id (in prose) |

## Accessibility in Documentation

### Text Accessibility

1. Do not rely on color alone to convey meaning. Use text labels with color. [general]
2. Provide alt text for all images. Describe what the image shows and why it matters. [general]
3. Use descriptive link text: "See the authentication guide" not "Click here". [general]
4. Structure content with proper heading hierarchy for screen readers. [general]
5. Ensure sufficient contrast in any embedded diagrams or images. [general]

### Inclusive Language

| Avoid | Use Instead |
| --- | --- |
| Whitelist/blacklist | Allowlist/denylist |
| Master/slave | Primary/replica, leader/follower |
| Sanity check | Validation, verification |
| Dummy value | Placeholder, example value |
| Crippled | Degraded, limited |
| Grandfather clause | Legacy provision |

## Documentation Versioning

| Strategy | When to Use |
| --- | --- |
| Version dropdown | Multiple supported product versions |
| Latest-only | Single active version, backward-compatible |
| Date-stamped | Compliance or regulatory documentation |
| Git-tagged | Developer documentation in the same repo |

Rules: [general]
- Clearly label which version each page documents.
- Archive (do not delete) documentation for deprecated versions.
- Redirect old URLs to the latest version or an archive notice.

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| Inconsistent terminology | Reader confusion, search failure | Glossary and linting rules |
| Wall of text | Readers skip; miss critical information | Break into lists, tables, headings |
| Passive voice everywhere | Obscures who does what | Active voice: subject-verb-object |
| Screenshots without context | Break on UI changes; inaccessible | Describe the action; use screenshots as supplements |
| "Click here" links | Inaccessible; poor SEO | Descriptive link text |

## Grounding Checklist

Before publishing any documentation, verify: [observed]
- [ ] No em dashes, en dashes, or exclamation marks
- [ ] No filler words (simply, easily, just, obviously, clearly)
- [ ] Headings use sentence case and are unique within the page
- [ ] Lists have parallel structure
- [ ] Tables are used for comparisons and structured data
- [ ] All images have alt text
- [ ] Link text is descriptive (no "click here")
- [ ] Inclusive language throughout
- [ ] Terminology is consistent (check against glossary)
- [ ] Sentences are under 25 words
