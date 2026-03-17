---
title: API Documentation Patterns
domain: technical-writing
subdomain: api-reference
audience: developers, technical writers, API designers
tags: [api, reference, openapi, rest, endpoints, schemas]
version: "1.0.0"
rag_chunk_strategy: section-based
last_updated: "2026-03-17"
---

# API Documentation Patterns

## Purpose

Provide reusable patterns for writing API reference documentation that developers can scan, trust, and integrate from without supplementary support. [general]

## Structure Template

Every API endpoint document follows this skeleton. [observed]

| Section | Required | Description |
| --- | --- | --- |
| Endpoint summary | Yes | One sentence: verb + resource + purpose |
| Authentication | Yes | Auth method, scopes, token format |
| Request | Yes | Method, path, headers, parameters, body schema |
| Response | Yes | Status codes, body schema, error codes |
| Code examples | Yes | Minimum one language, prefer three |
| Rate limits | Conditional | Include when rate limits apply |
| Versioning | Conditional | Include when multiple API versions exist |
| Deprecation notice | Conditional | Include when endpoint is deprecated |

## Endpoint Summary Rules

1. Start with an HTTP verb in imperative form: "Creates", "Retrieves", "Deletes". [general]
2. Name the resource explicitly: "Creates a user session", not "Creates a new item". [general]
3. State the business outcome: "Retrieves the payment status for a given transaction ID". [general]
4. Maximum length: one sentence, under 120 characters. [observed]

## Request Documentation

### Path Parameters

```
GET /api/v1/users/{user_id}/orders/{order_id}
```

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| user_id | string (UUID) | Yes | Unique identifier of the user |
| order_id | string (UUID) | Yes | Unique identifier of the order |

Rules for path parameters: [general]
- Always specify the type and format (string, integer, UUID, slug).
- Mark required/optional explicitly.
- Provide a realistic example value, never "string" or "123".

### Query Parameters

Document each query parameter with type, default, constraints, and an example. [general]

```
GET /api/v1/orders?status=pending&page=1&per_page=25
```

| Parameter | Type | Default | Constraints | Description |
| --- | --- | --- | --- | --- |
| status | string | all | Enum: pending, completed, cancelled | Filter orders by status |
| page | integer | 1 | Min: 1 | Page number for pagination |
| per_page | integer | 25 | Min: 1, Max: 100 | Results per page |

### Request Body

Use JSON Schema notation with required fields marked. Include a complete, realistic example. [general]

```json
{
  "name": "Acme Corp",
  "email": "billing@acme.example.com",
  "plan": "enterprise",
  "billing_address": {
    "street": "123 Main St",
    "city": "Cincinnati",
    "state": "OH",
    "zip": "45202"
  }
}
```

Rules: [observed]
- Show the full object, not partial fragments.
- Use realistic data (not "string", "test", or placeholder values).
- Annotate nullable fields and default values.

## Response Documentation

### Status Codes

Document every status code the endpoint can return. [general]

| Status | Meaning | When |
| --- | --- | --- |
| 200 OK | Success | Request completed, body contains result |
| 201 Created | Resource created | POST succeeded, Location header set |
| 400 Bad Request | Validation error | Missing required field or invalid format |
| 401 Unauthorized | Auth failure | Missing or expired token |
| 403 Forbidden | Insufficient scope | Valid token, insufficient permissions |
| 404 Not Found | Resource missing | ID does not match any record |
| 429 Too Many Requests | Rate limited | Retry after Retry-After header value |
| 500 Internal Server Error | Server fault | Unexpected failure; include correlation ID |

### Error Response Schema

Standardize error responses across all endpoints. [general]

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'email' must be a valid email address",
    "details": [
      {
        "field": "email",
        "constraint": "format",
        "value": "not-an-email"
      }
    ],
    "request_id": "req_abc123def456"
  }
}
```

## Code Examples

### Rules

1. Provide examples in at least one language (prefer: cURL, Python, JavaScript). [general]
2. Use the same realistic data from the request body section. [observed]
3. Include authentication headers in every example. [general]
4. Show the complete request, not abbreviated fragments. [general]

### cURL Example Template

```bash
curl -X POST https://api.example.com/v1/users \
  -H "Authorization: Bearer sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "email": "billing@acme.example.com",
    "plan": "enterprise"
  }'
```

### Python Example Template

```python
import requests

response = requests.post(
    "https://api.example.com/v1/users",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "name": "Acme Corp",
        "email": "billing@acme.example.com",
        "plan": "enterprise",
    },
)
data = response.json()
```

## Authentication Documentation

| Item | Describe |
| --- | --- |
| Auth method | Bearer token, API key, OAuth2, mTLS |
| Token location | Header, query param, cookie |
| Token format | JWT structure, key prefix (sk_live_, pk_test_) |
| Scopes | Required scopes for this endpoint |
| Expiration | Token lifetime and refresh mechanism |
| Error behavior | 401 vs 403 distinction |

## OpenAPI/Swagger Integration

When maintaining OpenAPI specs alongside prose docs: [general]
- OpenAPI is the source of truth for schemas and endpoints.
- Prose documentation adds context, use cases, and examples that OpenAPI cannot express.
- Auto-generate reference docs from OpenAPI; hand-write conceptual guides.
- Version the OpenAPI spec in the same repository as the code.

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
| --- | --- | --- |
| "See the code for details" | Developers should not read source to use an API | Document every public contract |
| Placeholder example data | "string", "test123" teaches nothing | Use realistic, domain-relevant data |
| Missing error documentation | Developers cannot handle failures they do not know about | Document every error code |
| Outdated examples | Broken examples destroy trust | CI-test all code examples |
| Auth documented elsewhere | Developers cannot find what they need | Include auth in every endpoint page |

## Grounding Checklist

Before publishing API documentation, verify: [observed]
- [ ] Every endpoint has method, path, summary, auth, request, response, and example
- [ ] All status codes the endpoint can return are documented
- [ ] Request and response schemas match the actual implementation
- [ ] Code examples execute successfully against a test environment
- [ ] Rate limits and pagination are documented where applicable
- [ ] Error response format is consistent across all endpoints
