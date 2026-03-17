# Suggestions

Improvement proposals for the audhd-agents system. Each suggestion is ranked by implementation effort and cognitive-load impact.

---

## GitHub Integration

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| G-1 | **Add `engineering-github-pr-reviewer` skill** — accept a PR number + repo, fetch diff, route to `engineering-code-reviewer` | Medium | High | Closes the loop from listing to reviewing |
| G-2 | **Add `author` auto-resolution** — when no author filter is supplied, infer from `GITHUB_ACTOR` env var or `.env` | Low | Medium | Removes a recurring manual step |
| G-3 | **Add GitHub MCP adapter** — `adapters/github_adapter.py` wrapping `gh` CLI or `PyGitHub` for live API calls | High | High | Enables real-time PR data instead of LLM-generated responses |
| G-4 | **Add `engineering-github-issue-lister` skill** — same schema pattern as `engineering-github-pr-lister` for issues | Low | Medium | Reuse schema and prompt structure |
| G-5 | **Add `draft` flag filter to `engineering-github-pr-lister`** — include/exclude draft PRs | Low | Low | Draft PRs create noise during triage |
| G-6 | **Add PR status summary hook** — a pre-execute hook that fetches open PR count and injects it as context | Medium | Medium | Eliminates the need to explicitly invoke the skill for quick status checks |

---

## Skill Architecture

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| S-1 | **Add `limit` field to `_base/schema_base.json`** — pagination is common; centralising avoids per-skill duplication | Low | Medium | `engineering-github-pr-lister` already implements it locally |
| S-2 | **Add `sort` field to research-category skills** — `created`, `updated`, `popularity` | Low | Medium | Needed for any listing skill |
| S-3 | **Add `SK-PAGINATE` hook** — auto-fetches next page when result count equals limit | High | Medium | Removes manual re-invocation for large result sets |
| S-4 | **Standardise `items` array in output schemas** — all listing skills should use `{items: [], total: int}` envelope | Low | High | Consistency across `github-pr-lister`, future `issue-lister`, `release-lister` |
| S-5 | **Add `next_action` auto-generation for listing skills** — surface the highest-priority item as the suggested next action | Low | High | PROFILE.md: executive function offload |

---

## Routing and Capability Graph

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| R-1 | **Add `list`, `show`, `fetch`, `get` triggers to `routing_rules.yaml`** — currently unrouted for listing intents | Low | High | Implemented in this PR |
| R-2 | **Add `github` as a trigger keyword** — route to `research` capability | Low | Medium | Implemented in this PR |
| R-3 | **Add `pull request`, `PR`, `merge request` trigger phrases** | Low | High | Implemented in this PR |
| R-4 | **Add `research` chain to `capability_graph.yaml`** — `research > synthesize` for listing + summarising workflows | Low | Medium | Currently no chain uses `research` as a standalone entry |

---

## Cognitive Runtime

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| C-1 | **Add `SK-LIST` hook** — reduce any listing output to 3 items when `energy_level=low` | Low | High | Aligns with LOW energy constraint: 3 bullet max |
| C-2 | **Add crash-mode state persistence** — save last `skill_id` + `input_text` to disk for resume | Medium | High | PROFILE.md: Where Was I protocol; currently crash just returns one sentence |
| C-3 | **Add `context_switches` auto-increment in router** — currently caller-supplied; should be tracked server-side | Medium | Medium | Monotropism guard requires accurate switch count |
| C-4 | **Add `task_tier` auto-classification for listing tasks** — listing is always T1; should not require caller to specify | Low | Medium | Reduces cognitive overhead per request |
| C-5 | **Add session-scoped thread anchoring** — persist `active_thread` across consecutive requests in same session | High | High | Monotropism: one thread, no silent switches |

---

## Testing

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| T-1 | **Add `test_skill_schema.py`** — validate all `schema.json` files load and resolve `allOf/$ref` without error | Low | High | Catches broken references before CI manifest build |
| T-2 | **Add `test_routing_rules.py`** — verify every trigger phrase in `routing_rules.yaml` matches at least one registered skill | Low | Medium | Currently routing rules are untested |
| T-3 | **Add `test_examples.py`** — load every `examples.json` and validate inputs satisfy the skill's schema | Low | High | Catches schema drift when skills are updated |
| T-4 | **Add `test_build_manifest.py`** — run `build.py` programmatically and assert output matches committed `dist/` | Low | Medium | Currently only checked via `git diff --exit-code` in CI |
| T-5 | **Add energy-level contract test** — assert LOW energy output is always ≤ 3 bullets, CRASH output is always empty or deferred | Medium | High | PROFILE.md contracts are not programmatically verified |

---

## Developer Experience

| # | Suggestion | Effort | Impact | Notes |
| --- | --- | --- | --- | --- |
| D-1 | **Add `sk new-skill <name> <capability>`** CLI command — scaffolds all four files from templates | Medium | High | New skills currently require copying an existing skill manually |
| D-2 | **Add `sk validate <skill-name>`** — check schema resolves, prompt.md has all required sections, examples match schema | Low | High | Catches mistakes before CI |
| D-3 | **Add `CHANGELOG.md`** — track skill additions and breaking schema changes | Low | Medium | Currently no change history for skills |
| D-4 | **Update `CAPABILITIES.md` skill count automatically in `build.py`** — count drifts as skills are added | Low | Low | Currently manually maintained |
| D-5 | **Add `--dry-run` flag to `build.py`** — show what would be written without touching `dist/` | Low | Medium | Useful before committing manifests |
