# GitHub PR Lister

## Goal

Return a structured list of the latest open pull requests for a GitHub repository, ordered by creation date descending. Include PR number, title, author, labels, and URL.

## Energy Levels

### HIGH

- Return full PR metadata: number, title, author, labels, milestone, created_at, updated_at, draft status, URL, and head branch.
- Include a one-line summary of each PR's purpose inferred from the title.
- Group results by label or author when a filter is applied.

### MEDIUM

- Return core fields: number, title, author, labels, created_at, and URL.
- List up to 10 PRs unless a limit is specified.

### LOW

- Return minimal fields: number, title, and URL only.
- List up to 5 PRs.

### CRASH

- Defer listing. Return empty pull_requests array with a note to retry when energy recovers.

## Pattern Compression

- **Verdict First**: State total count of open PRs before listing details.
- **Confidence Statement**: Tag results as `[observed]` when drawn directly from API data.
- **Falsification Conditions**: Results may be stale if fetched more than 5 minutes ago.

## Monotropism Guards

Focus on the single repository thread provided. Do not expand scope to related repositories or issues unless explicitly asked.

## Working Memory

- [ ] Parse repository identifier from input_text (owner/repo or URL)
- [ ] Apply author filter if provided
- [ ] Apply label filter if provided
- [ ] Apply limit (default 10)
- [ ] Sort by created_at descending
- [ ] Return structured output

## Anti-patterns

Avoid:
1. Returning closed or merged PRs when the request is for open PRs.
2. Truncating PR titles or URLs.
3. Inferring PR status without explicit API confirmation.

## Claim Tags

- [observed]: Data returned directly from GitHub API.
- [inferred]: Fields derived or inferred from available data.
- [general]: Background knowledge about PR workflows.
- [unverified]: Estimates or assumptions not confirmed by API.

## Where Was I? Protocol

On session resume, state:
- LAST CONTEXT: Repository and filters used in prior request.
- CURRENT STATE: Number of PRs returned, any applied filters.
- NEXT ACTION: Re-fetch with same or updated parameters.

## Output Structure

```json
{
  "pull_requests": {
    "repository": "owner/repo",
    "total_open": 0,
    "filters_applied": {
      "author": null,
      "label": null,
      "limit": 10
    },
    "items": [
      {
        "number": 0,
        "title": "string",
        "author": "string",
        "labels": [],
        "created_at": "ISO8601",
        "updated_at": "ISO8601",
        "url": "string",
        "draft": false
      }
    ]
  }
}
```
