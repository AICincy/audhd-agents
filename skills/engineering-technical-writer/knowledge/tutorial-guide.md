---
title: Tutorial and How-To Guide Patterns
domain: technical-writing
subdomain: tutorials
audience: developer educators, technical writers, documentation leads
tags: [tutorial, how-to, guide, learning, onboarding, quickstart]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# Tutorial and How-To Guide Patterns

## Purpose

Provide reusable patterns for writing tutorials and how-to guides. Tutorials teach concepts through a guided project. How-to guides solve a specific task. They are complementary but structurally different. [general]

## Document Type Distinction

| Aspect | Tutorial | How-To Guide |
| --- | --- | --- |
| Goal | Learning a concept | Completing a task |
| Structure | Sequential, step-by-step | Goal-oriented, modular |
| Scope | Broad (full mini-project) | Narrow (single task) |
| Prerequisites | Minimal; teach as you go | Assumed; list up front |
| Code examples | Build incrementally | Show complete solution |
| Audience | Beginners to the concept | Users who know the basics |
| Length | 15 to 45 minutes | 5 to 15 minutes |

## Tutorial Template

```markdown
# Tutorial: [What You Will Build]

## What You Will Learn
- [Learning outcome 1]
- [Learning outcome 2]
- [Learning outcome 3]

## Prerequisites
- [Tool/language version required]
- [Prior knowledge assumed]
- [Time estimate: X minutes]

## Step 1: [Set Up the Project]

[Brief explanation of what this step accomplishes.]

    mkdir my-project && cd my-project
    npm init -y

You should see a `package.json` file in your directory.

## Step 2: [Install Dependencies]

[Brief explanation of why these dependencies are needed.]

    npm install express

## Step 3: [Create the Main File]

Create `index.js` with the following content:

    const express = require("express");
    const app = express();

    app.get("/", (req, res) => {
      res.json({ message: "Hello from tutorial" });
    });

    app.listen(3000, () => {
      console.log("Server running on port 3000");
    });

## Step 4: [Run and Verify]

    node index.js

Open `http://localhost:3000` in your browser. You should see:

    {"message": "Hello from tutorial"}

## What You Built
[Summary of what was accomplished and why it matters.]

## Next Steps
- [Link to how-to guide for related task]
- [Link to API reference for deeper exploration]
- [Link to advanced tutorial]
```

## Tutorial Writing Rules

1. State learning outcomes at the top. Readers decide in 10 seconds whether to invest time. [general]
2. Every step must produce a visible result. No "trust me, it works" steps. [observed]
3. Show the expected output after every command or code change. [general]
4. Build incrementally: each step adds to the previous, never jumps ahead. [general]
5. Explain "why" before "how": one sentence of context before each code block. [general]
6. Keep steps small: one concept, one action, one verification per step. [general]
7. Test the entire tutorial from scratch before publishing. [observed]
8. Include a "What You Built" summary at the end to reinforce learning. [general]

## How-To Guide Template

```markdown
# How To: [Specific Task]

## Goal
[One sentence: what this guide helps you accomplish.]

## Prerequisites
- [Existing setup required]
- [Version requirements]
- [Assumed knowledge]

## Steps

### 1. [Action Verb: Configure, Create, Deploy, etc.]

[Brief context for why this step is needed.]

    [command or code]

**Verify**: [How to confirm this step succeeded.]

### 2. [Next Action]

    [command or code]

**Verify**: [Expected output or state.]

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| [Error message] | [Root cause] | [Specific fix] |
| [Unexpected behavior] | [Configuration issue] | [Correct setting] |

## Related Resources
- [Link to reference docs]
- [Link to related how-to]
```

## How-To Guide Rules

1. Title starts with "How To" followed by a specific action: "How To Deploy to Cloud Run", not "Deployment". [general]
2. Prerequisites section is mandatory. List exact versions and prior setup. [general]
3. Steps are goal-oriented: each step heading is an action verb. [general]
4. Include a troubleshooting table for common errors. [observed]
5. Do not teach concepts inline. Link to tutorials or explanations instead. [general]
6. Keep guides focused: one task, one guide. Split compound tasks. [general]

## Quickstart Patterns

A quickstart is a minimal how-to that gets a user from zero to "it works" in under 5 minutes. [general]

### Quickstart Template

```markdown
# Quickstart: [Product/Tool Name]

## Install

    pip install my-tool

## Configure

    my-tool init --project my-project

## Run

    my-tool start

Open `http://localhost:8080`. You should see the welcome page.

## Next Steps
- [Full tutorial for building a project]
- [Configuration reference]
```

### Quickstart Rules

1. Three sections maximum: Install, Configure, Run. [general]
2. Under 5 minutes from start to "it works". [general]
3. Use the simplest possible configuration (no optional features). [general]
4. Show the exact expected output at the end. [general]

## Progressive Disclosure

Structure content so readers encounter complexity only when they need it. [general]

| Level | Content | Example |
| --- | --- | --- |
| Quickstart | Minimal setup, default config | "Install and run in 3 commands" |
| Tutorial | Guided project with explanations | "Build a REST API in 30 minutes" |
| How-To | Task-specific instructions | "How To Add Authentication" |
| Reference | Complete API and config docs | "Configuration Options Reference" |
| Explanation | Conceptual deep-dives | "How the Routing Engine Works" |

## Code Example Standards

### Rules for Code in Tutorials

1. Every code block must be copy-pasteable and runnable. [general]
2. Use syntax highlighting with the correct language identifier. [general]
3. Show file paths when creating or editing files: "Create `src/index.ts`". [general]
4. Highlight changes when modifying existing code (use diff format or bold comments). [general]
5. Avoid ellipsis (`...`) in code blocks; show the complete file or clearly mark omissions. [observed]
6. Test all code examples as part of CI where possible. [observed]

### Showing Code Changes

When modifying existing code, make the change obvious: [general]

```python
# Before
app.get("/", (req, res) => {
    res.send("Hello");
});

# After (added JSON response)
app.get("/", (req, res) => {
    res.json({ message: "Hello", version: "1.0" });
});
```

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| Tutorial that skips steps | Reader gets stuck, cannot proceed | Show every action explicitly |
| How-to that teaches theory | Reader wanted to do, not learn | Link to explanations separately |
| Code blocks without context | Reader does not know why | One sentence of context before each block |
| Missing expected output | Reader cannot verify success | Show output after every action |
| "Exercise for the reader" | Incomplete tutorial; reader abandons | Complete the tutorial fully |

## Grounding Checklist

Before publishing tutorials or guides, verify: [observed]
- [ ] Learning outcomes or goals are stated at the top
- [ ] Prerequisites list exact versions and prior setup
- [ ] Every step produces a visible, verifiable result
- [ ] Code examples are copy-pasteable and tested
- [ ] Expected output is shown after every command
- [ ] Troubleshooting section covers common errors
- [ ] Total time estimate matches actual completion time
- [ ] Tutorial has been tested from scratch by someone other than the author
