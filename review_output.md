Hook warnings for engineering-code-reviewer: ['Unknown hook: SK-CODEREVIEW']
Hook warnings for engineering-code-reviewer: ['Unknown hook: SK-CODEREVIEW']
Hook warnings for engineering-code-reviewer: ['Unknown hook: SK-CODEREVIEW']
Initializing SkillRouter...

--- Reviewing runtime/planner.py ---
[runtime/planner.py] Review Result (Model: claude-opus-4-6):
{
  "review": {
    "description": "RuntimePlanner: YAML-based intent-to-capability routing with trigger matching and skill resolution",
    "files_count": 1,
    "risk_level": "medium",
    "findings": [
      {
        "severity": "HIGH",
        "location": "planner.py:20-35",
        "issue": "YAML deserialization with yaml.safe_load on untrusted or operator-editable files without schema validation",
        "impact": "Malformed YAML silently produces wrong types: `rules` could be a string or int instead of List[Dict], `chains` could be a list instead of Dict[str, List[str]]. Downstream code (.get on a non-dict, iteration over non-list) raises unhandled TypeError/AttributeError at runtime, not at load time. Debugging is painful because the error surfaces far from the cause.",
        "fix": "Validate structure after load. Minimum: assert isinstance(data, dict), assert isinstance(self.rules, list), assert all entries in self.rules are dicts with expected keys. Consider pydantic models for the config schema. Reject and log on validation failure rather than silently accepting partial state.",
        "tag": "[DRV]"
      },
      {
        "severity": "HIGH",
        "location": "planner.py:20-35",
        "issue": "Silent degradation on config load failure: exceptions are logged but execution continues with empty rules/chains",
        "impact": "If both files fail to load (permissions, corrupt YAML, missing dependency), the planner initializes successfully but is inert. Every call to plan_execution_chain returns []. No caller can distinguish 'planner loaded but no rules matched' from 'planner is broken'. This violates fail-fast principles and makes debugging production issues significantly harder.",
        "fix": "Option A: Raise on config load failure (fail fast). Option B: Expose a health/readiness property (e.g., `self.healthy: bool`) that callers and /readyz can check. Option C: At minimum, log at CRITICAL level and set a degraded flag. The current pattern of logging at ERROR and continuing is the worst middle ground.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "planner.py:43-58",
        "issue": "First-match trigger semantics with substring matching creates ordering-dependent, ambiguous routing",
        "impact": "If rules contain triggers ['error', 'error log'], the trigger 'error' matches input 'show me the error log' first, potentially routing to the wrong chain. Substring matching also means trigger 'is' matches 'this is a test'. Rule ordering in the YAML file silently controls priority with no explicit rank mechanism. As the rule set grows, this becomes a source of subtle, hard-to-reproduce misrouting.",
        "fix": "1) Add an explicit `priority` field to rules and sort on load. 2) Consider whole-word or regex matching instead of bare `in`. 3) Log all matched rules (not just first) at DEBUG level so ambiguity is observable. 4) The comment acknowledges embedding similarity as a future path; until then, document the ordering contract.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "planner.py:48-49",
        "issue": "No type guard on rule['trigger']: if a YAML rule has `trigger: 'single_string'` instead of a list, iteration yields individual characters",
        "impact": "Each character of the string becomes a trigger. 'e', 'r', 'r', 'o', 'r' would each be tested as substring matches against input. Nearly any input would match. Silent, bizarre behavior.",
        "fix": "After loading, validate that each rule's `trigger` is a list. Coerce single strings to [string] if desired, or reject with a clear error message.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "planner.py:55-56",
        "issue": "chains values returned by reference, not by copy",
        "impact": "Callers receiving `self.chains[default_chain_name]` get a mutable reference to the planner's internal state. Any caller that appends/modifies the returned list corrupts the planner for all subsequent calls. This is a shared-mutable-state bug waiting to happen.",
        "fix": "Return `list(self.chains[default_chain_name])` to return a shallow copy.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "planner.py:63-72",
        "issue": "resolve_capability_to_skill returns first arbitrary match from dict iteration order",
        "impact": "Dict iteration order is insertion order in Python 3.7+, but the caller has no control over which skill is selected when multiple skills declare the same capability. No scoring, no tier matching, no energy-aware routing. The docstring acknowledges this gap but the current behavior is nondeterministic from the caller's perspective if the map is built from multiple sources.",
        "fix": "Short term: document that insertion order is the tiebreaker and ensure the map is built in priority order. Medium term: accept a scoring function or filter predicate (energy level, task tier) as a parameter.",
        "tag": "[DRV]"
      },
      {
        "severity": "LOW",
        "location": "planner.py:14",
        "issue": "Constructor accepts str paths but never accepts Path objects",
        "impact": "Minor ergonomic issue. Callers using pathlib throughout must convert to str. Inconsistent with the internal use of Path().",
        "fix": "Type hint as `Union[str, Path]` or just `Path`, and wrap with `Path()` internally (which is idempotent on Path inputs).",
        "tag": "[OBS]"
      },
      {
        "severity": "LOW",
        "location": "planner.py:1-6",
        "issue": "No __all__ export; no module docstring",
        "impact": "Minor. Reduces discoverability and IDE support for public API surface.",
        "fix": "Add `__all__ = ['RuntimePlanner']` and a module-level docstring.",
        "tag": "[OBS]"
      }
    ],
    "open_questions": [
      "Is routing_rules.yaml operator-editable at runtime, or only at deploy time? If runtime-editable, the lack of schema validation (finding 1) escalates to CRITICAL.",
      "Are there callers that mutate the returned chain list? If so, finding 5 is actively exploitable now.",
      "What is the intended behavior when config files are missing: graceful degradation or hard failure? Current code implies graceful, but no contract is documented."
    ],
    "test_gaps": [
      "No test coverage for malformed YAML (wrong types, missing keys, empty files, non-dict top-level)",
      "No test for trigger ordering ambiguity (multiple rules matching same input)",
      "No test for single-string trigger vs list-of-strings trigger",
      "No test for chain mutation after return (shared reference bug)",
      "No test for resolve_capability_to_skill when multiple skills declare the same capability"
    ],
    "summary": "Structurally sound for a prototype but carries two HIGH-severity issues around silent failure modes: unvalidated YAML schema and silent degradation on load failure. Both will cause hard-to-diagnose production bugs. The substring trigger matching is a known limitation (documented in comments) but needs guardrails before the rule set grows. Returning mutable internal state is a latent shared-state bug. Recommended priority: (1) add schema validation on load, (2) expose planner health status, (3) copy chains on return, (4) guard trigger types."
  }
}

--- Reviewing runtime/schemas.py ---
[runtime/schemas.py] Review Result (Model: claude-opus-4-6):
{
  "review": {
    "description": "Audit of runtime/schemas.py for cognitive contract adherence, robustness, and typing",
    "files_count": 1,
    "risk_level": "medium",
    "findings": [
      {
        "severity": "HIGH",
        "location": "schemas.py:CognitiveState.resume_from",
        "issue": "No validation enforces that resume_from is provided when session_context is RESUMED or INTERRUPTED, or that it is absent/null when session_context is NEW",
        "impact": "A request with session_context='resumed' and resume_from=None will pass validation silently. The Where Was I protocol (SK-RESUME) would then execute without a checkpoint ID, likely causing a KeyError or silent no-op downstream. Conversely, resume_from with session_context='new' is semantically incoherent but accepted. [DRV]",
        "fix": "Add a Pydantic model_validator(mode='after') that raises ValueError when (a) needs_resume() is True and resume_from is None, or (b) session_context is NEW and resume_from is not None. Example:\n\n@model_validator(mode='after')\ndef _validate_resume_consistency(self) -> CognitiveState:\n    if self.needs_resume() and self.resume_from is None:\n        raise ValueError('resume_from required when session_context is resumed or interrupted')\n    if self.session_context == SessionContext.NEW and self.resume_from is not None:\n        raise ValueError('resume_from must be None for new sessions')\n    return self",
        "tag": "[DRV]"
      },
      {
        "severity": "HIGH",
        "location": "schemas.py:ExecuteResponse.energy_level",
        "issue": "energy_level field has no default value and no default_factory, yet every other field on ExecuteResponse has a default",
        "impact": "Any code path that constructs ExecuteResponse without explicitly passing energy_level will raise a ValidationError at runtime. This is especially dangerous for error-handling paths and crash-mode construction where the caller might assemble the response incrementally. Every other field is optional or defaulted, so this is the only field that will blow up if omitted. [OBS]",
        "fix": "Either add a default (default=EnergyLevel.MEDIUM) to match CognitiveState's default, or make it Optional[EnergyLevel] with default=None for error paths. The former is safer since crash_state already signals crash mode distinctly.",
        "tag": "[OBS]"
      },
      {
        "severity": "MEDIUM",
        "location": "schemas.py:ExecuteRequest.input_text",
        "issue": "input_text is required (Field(...)) with no length constraints",
        "impact": "An empty string passes validation. An extremely large string (megabytes) also passes, creating a potential resource exhaustion vector when forwarded to model providers. Provider APIs have their own token limits, but the damage (serialization cost, logging bloat, memory allocation) happens before the provider rejects it. [DRV]",
        "fix": "Add min_length=1 and max_length constraints. Suggested: Field(..., min_length=1, max_length=100_000). Tune max_length to the largest reasonable input for any skill.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "schemas.py:ExecuteRequest.skill_id",
        "issue": "skill_id is Optional with no format validation. Description says 'e.g. engineering-code-reviewer' but any string (including path traversal patterns like '../../etc/passwd') is accepted",
        "impact": "If skill_id is used downstream to construct file paths (loading skill configs from a skills/ directory), unsanitized input enables path traversal. Even without path traversal, whitespace, special characters, or empty strings could cause silent routing failures. [DRV]",
        "fix": "Add a pattern constraint: Field(default=None, pattern=r'^[a-z0-9][a-z0-9\\-]{0,63}$'). This enforces slug-format IDs and prevents injection.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "schemas.py:ExecuteRequest.request_id",
        "issue": "request_id accepts any string, not just valid UUIDs. The default_factory generates a UUID, but a caller can pass 'hello' or an empty string",
        "impact": "Downstream tracing, logging, and correlation ID matching may break or produce ambiguous results if request_id is not a valid UUID. Log injection is also possible if the string contains newlines or control characters. [DRV]",
        "fix": "Either type it as uuid.UUID (Pydantic serializes/deserializes automatically) or add a validator that parses the string as UUID4. If non-UUID trace IDs must be supported, at minimum add min_length=1 and a pattern excluding control characters.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "schemas.py:ExecuteResponse",
        "issue": "No invariant enforces that crash_state is populated when energy_level is CRASH, or that output/model_used are empty/None in crash mode",
        "impact": "The docstring and CrashStateResponse description say 'populated only when energy_level is CRASH', but nothing enforces this. A bug in the response construction could return crash_state=None with energy_level=CRASH (client sees no crash info) or crash_state populated with energy_level=HIGH (contradictory signal). [DRV]",
        "fix": "Add a model_validator(mode='after') on ExecuteResponse:\n\n@model_validator(mode='after')\ndef _validate_crash_consistency(self) -> ExecuteResponse:\n    if self.energy_level == EnergyLevel.CRASH:\n        if self.crash_state is None:\n            raise ValueError('crash_state required when energy_level is CRASH')\n        if self.model_used is not None:\n            raise ValueError('model_used must be None in crash mode')\n    elif self.crash_state is not None:\n        raise ValueError('crash_state must be None when not in crash mode')\n    return self",
        "tag": "[DRV]"
      },
      {
        "severity": "LOW",
        "location": "schemas.py:ExecuteResponse.input_tokens, output_tokens, latency_ms",
        "issue": "Numeric fields accept negative values",
        "impact": "Negative token counts or latency are semantically invalid and could corrupt metrics aggregation or billing calculations downstream. [DRV]",
        "fix": "Use Field(default=0, ge=0) for all three fields. For latency_ms, ge=0.0.",
        "tag": "[DRV]"
      },
      {
        "severity": "LOW",
        "location": "schemas.py:CognitiveCompliance",
        "issue": "compliant defaults to True independently of violations list. A CognitiveCompliance(violations=['no em dashes']) would report compliant=True with violations present",
        "impact": "Consumers checking only the boolean flag would miss violations. This is a semantic inconsistency that could mask contract breaches in downstream monitoring. [DRV]",
        "fix": "Add a model_validator or computed field: compliant should be derived from len(violations) == 0, not independently settable. Either make compliant a @computed_field or add a validator that overrides it based on violations.",
        "tag": "[DRV]"
      },
      {
        "severity": "LOW",
        "location": "schemas.py:ExecuteResponse.request_id",
        "issue": "Defaults to empty string rather than None or auto-generated UUID",
        "impact": "If the response construction path forgets to copy request_id from the request, the response ships with request_id='' which is a valid but useless trace ID. Correlation between request and response breaks silently. [OBS]",
        "fix": "Either default to default_factory=lambda: str(uuid.uuid4()) to match the request pattern, or make it Optional[str] = None so the absence is explicit rather than hidden behind an empty string.",
        "tag": "[OBS]"
      },
      {
        "severity": "LOW",
        "location": "schemas.py:top-level",
        "issue": "No model_config with strict mode, JSON schema customization, or frozen models for response types",
        "impact": "Response models are mutable after construction, which is rarely intentional for API responses. Without model_config = ConfigDict(frozen=True) on response models, downstream code could accidentally mutate response objects. Without strict=True on request models, coercion silently converts '123' to 123 for int fields, which may mask client bugs. [GEN]",
        "fix": "Add model_config = ConfigDict(frozen=True) to all response models (ExecuteResponse, CrashStateResponse, CognitiveCompliance). Consider ConfigDict(strict=True) on ExecuteRequest if you want to reject type coercion.",
        "tag": "[GEN]"
      }
    ],
    "open_questions": [
      "How is skill_id resolved downstream? If it maps to filesystem paths, the path traversal risk in finding #4 escalates to HIGH.",
      "Is there a separate validation layer (e.g., FastAPI dependency) that catches the resume_from inconsistency before the handler runs, or is the schema the only gate?",
      "Are ExecuteResponse objects ever serialized to a cache or event store? If so, the mutable model concern becomes more urgent."
    ],
    "test_gaps": [
      "No evidence of tests for cross-field validation (resume_from vs session_context, crash_state vs energy_level, compliant vs violations)",
      "No evidence of boundary tests for input_text (empty string, max length, unicode edge cases)",
      "No evidence of tests for request_id format validation or injection resistance",
      "No evidence of negative-value tests for token counts and latency"
    ],
    "summary": "Schema design aligns well with the cognitive contract: enums map cleanly to AGENT.md routing, CognitiveState is a first-class parameter, crash mode has a dedicated response shape. The two HIGH findings are cross-field invariants that the schema documents in prose but does not enforce in code (resume_from consistency, energy_level missing default). The MEDIUM findings address input sanitization gaps that matter for a public-facing API. All fixes are additive Pydantic validators; no structural changes needed."
  }
}

--- Reviewing adapters/router.py ---
[adapters/router.py] Review Result (Model: claude-opus-4-6):
{
  "review": {
    "description": "Audit of adapters/router.py (SkillRouter) for cognitive contract adherence, robustness, and typing. AUDIT_ID: audit-engineering-code-reviewer-15712",
    "files_count": 1,
    "risk_level": "high",
    "findings": [
      {
        "severity": "CRITICAL",
        "location": "execute:model_chain loop, ~line 230",
        "issue": "Unguarded `result['input_tokens']` / `result['output_tokens']` / `result['latency_ms']` access. If any adapter returns a dict missing these keys, the entire failover chain aborts with a KeyError inside the try/except that catches Exception and silently continues to the next model. The KeyError is swallowed, `last_error` is set, and the next adapter is tried; if all adapters return dicts missing a key, the generic 'All models failed' RuntimeError is raised with a misleading KeyError as cause, hiding the real issue.",
        "impact": "Silent data loss on successful LLM calls; misleading error propagation; impossible to diagnose in production.",
        "fix": "Use `result.get('input_tokens', 0)` etc., or validate the adapter response shape before constructing SkillResponse. Better: define a typed adapter response dataclass and validate at the adapter boundary.",
        "tag": "[OBS]"
      },
      {
        "severity": "CRITICAL",
        "location": "execute:cognitive_state_override injection, ~line 185-191",
        "issue": "Mutates `request.options` in place. If the caller reuses the same SkillRequest object (e.g., retry logic, execute_chain), cognitive state values from a previous call leak into subsequent calls. execute_chain explicitly calls `request.options.copy()` for step requests but passes the original `cognitive_state_override` through, and the override injection mutates the original request's options dict before the chain even starts.",
        "impact": "State pollution across chained or retried requests. Difficult to reproduce; manifests as wrong energy level or mode in later chain steps.",
        "fix": "Deep-copy `request.options` at the top of `execute` before mutation, or build a new options dict for the override values.",
        "tag": "[DRV]"
      },
      {
        "severity": "HIGH",
        "location": "execute:JSON parsing block, ~line 260-275",
        "issue": "JSON stripping logic is fragile. A response like ```` ```json\\n{...}\\n``` some trailing text```` will fail the `endswith('```')` check after the trailing text, leaving markdown fences in the content. Also, responses with nested markdown code blocks (LLM returning code review output containing fenced blocks) will be incorrectly stripped.",
        "impact": "Intermittent JSON parse failures on valid LLM output; `{\"raw\": content, \"error\": \"JSON parse failed\"}` returned to caller with no retry.",
        "fix": "Use a regex: `re.match(r'^```(?:json)?\\s*\\n(.+?)\\n```\\s*$', content, re.DOTALL)` to extract the inner block cleanly. Consider a dedicated `extract_json` utility with tests.",
        "tag": "[OBS]"
      },
      {
        "severity": "HIGH",
        "location": "_build_skill_map, ~line 72",
        "issue": "Bare `except Exception: continue` swallows all errors during skill discovery, including permission errors, malformed YAML, and encoding issues. No logging. A broken skill.yaml silently disappears from the registry.",
        "impact": "Skills silently unavailable in production with no diagnostic trail. Operator cannot determine why a skill is missing.",
        "fix": "Log the exception at WARNING level with the path: `logger.warning('Failed to load skill config %s: %s', path, e)`",
        "tag": "[OBS]"
      },
      {
        "severity": "HIGH",
        "location": "load_skill, ~line 115-130",
        "issue": "Synchronous blocking I/O (file reads) called from `execute` via `run_in_executor`. However, `load_skill` itself opens multiple files sequentially with no error handling beyond the implicit FileNotFoundError. If skill.yaml exists in `skill_map` but was deleted between map build and load, the raw exception propagates with no context.",
        "impact": "Unhandled FileNotFoundError with no skill_id context in the traceback; hard to diagnose in async stack traces.",
        "fix": "Wrap in try/except, raise a domain-specific error: `raise SkillNotFoundError(f'Skill {skill_id} config missing at {skill_dir}') from e`",
        "tag": "[DRV]"
      },
      {
        "severity": "HIGH",
        "location": "execute_chain, ~line 310-340",
        "issue": "Duplicate cognitive_state_override injection logic (copy-pasted from `execute`). The override is injected into `request.options`, then `execute` is called which injects it again. The values are written twice: once here mutating the original request, once inside `execute` mutating the step request's options.",
        "impact": "Maintenance hazard (two places to update); double mutation of the original request's options dict (see CRITICAL finding on state pollution).",
        "fix": "Remove the duplicate injection from `execute_chain`. Let `execute` handle it. Pass `cognitive_state_override` through only.",
        "tag": "[OBS]"
      },
      {
        "severity": "HIGH",
        "location": "execute:result.get('headers', {}).get('x-backoff'), ~line 250",
        "issue": "SK-SYS-RECOVER backoff is a fixed 2-second sleep with no jitter, no exponential increase, and no cap on how many times it triggers across the failover chain. If multiple models return x-backoff, the request accumulates 2s per model with no upper bound. Also, the `[RECOVERY_ACTIVE]` prefix is injected into content that may be valid JSON, breaking downstream parsing.",
        "impact": "Unbounded latency accumulation; JSON parse failure on recovery-tagged responses.",
        "fix": "Apply backoff before retry (not after success). Do not mutate content; attach recovery metadata to a separate field. Use jittered exponential backoff.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "resolve_alias, ~line 108",
        "issue": "Returns `(None, alias)` when alias has no `/` separator and is not in alias_map. Callers then do `provider_name not in self.adapters` which evaluates `None not in self.adapters` (True), so the model is skipped with a misleading error about provider 'None' not being available.",
        "impact": "Confusing error message; no clear indication that the alias itself is unresolvable vs. the provider being down.",
        "fix": "Raise a ValueError or return a sentinel that the caller checks explicitly: `if provider_name is None: last_error = ValueError(f'Cannot resolve alias {alias} to a provider'); continue`",
        "tag": "[OBS]"
      },
      {
        "severity": "MEDIUM",
        "location": "Type annotations throughout",
        "issue": "Multiple typing gaps: (1) `cognitive_state_override` parameter typed as bare `None` default with no type hint (should be `Optional[CognitiveState]` or the runtime schema type). (2) `execute` return in the failover loop uses `result` dict with no TypedDict or protocol. (3) `self.adapters` typed as `Dict[str, Any]` loses all adapter interface guarantees. (4) `load_skill` returns bare `dict` instead of a TypedDict or dataclass.",
        "impact": "No static analysis coverage on adapter responses, skill configs, or cognitive state. Mypy/pyright cannot catch the KeyError issues identified above.",
        "fix": "Define `AdapterResult(TypedDict)`, `SkillConfig(TypedDict)`, and type `cognitive_state_override: Optional[CognitiveState] = None`. Type `self.adapters: Dict[str, BaseAdapter]` where BaseAdapter is the protocol/ABC.",
        "tag": "[OBS]"
      },
      {
        "severity": "MEDIUM",
        "location": "_load_instruction_stack, ~line 170",
        "issue": "Five sequential `run_in_executor` calls, each reading a small file. Each call schedules a thread pool task and awaits it. For five small files (likely <100KB total), the thread pool overhead exceeds the I/O time. No caching; these files are re-read on every single request.",
        "impact": "Unnecessary latency per request (5 thread pool round-trips). Under load, thread pool contention.",
        "fix": "Cache instruction stack contents with a TTL or file-mtime check. Alternatively, read all files in a single executor call.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "execute_chain:state bridge, ~line 350",
        "issue": "The state bridge concatenates raw output with the original request in XML-like tags. If `raw_output` contains `</previous_step_output>` or `</original_request>` strings (plausible in code review output), the XML structure breaks and the next model may misparse the context.",
        "impact": "Chain corruption when intermediate outputs contain XML-like content.",
        "fix": "Use a delimiter that cannot appear in LLM output (e.g., a unique separator token), or escape the content, or use structured JSON for the bridge payload.",
        "tag": "[DRV]"
      },
      {
        "severity": "MEDIUM",
        "location": "get_status, ~line 145",
        "issue": "API key prefix exposed in status output (`key_preview = api_key[:8] + '...'`). For most API keys, the first 8 characters include the provider prefix and enough entropy to narrow the key space. If status endpoint is exposed via the FastAPI `/readyz` or diagnostics route, this leaks partial credentials.",
        "impact": "Partial credential exposure in diagnostic output.",
        "fix": "Reduce to 4 characters or show only the provider prefix (e.g., `sk-...`, `AIza...`). Better: show only a boolean `key_present: true/false`.",
        "tag": "[OBS]"
      },
      {
        "severity": "MEDIUM",
        "location": "execute_chain, ~line 315",
        "issue": "f-string in logger.info calls: `logger.info(f'Planned capability chain: {capabilities}')`. This evaluates the f-string even when INFO logging is disabled, wasting cycles. Multiple instances throughout execute_chain.",
        "impact": "Minor performance cost; violates logging best practice.",
        "fix": "Use lazy formatting: `logger.info('Planned capability chain: %s', capabilities)`",
        "tag": "[OBS]"
      },
      {
        "severity": "LOW",
        "location": "__init__, ~line 50",
        "issue": "`config_path` defaults to a relative path `'adapters/config.yaml'`. Working directory dependency makes the router fragile when invoked from different entry points (tests, CLI, uvicorn).",
        "impact": "FileNotFoundError in non-standard working directories.",
        "fix": "Resolve relative to `__file__`: `Path(__file__).parent / 'config.yaml'`, or require absolute path.",
        "tag": "[DRV]"
      },
      {
        "severity": "LOW",
        "location": "execute:audit_id generation, ~line 240",
        "issue": "`audit_id = f'audit-{request.skill_id}-{os.getpid()}'` is not unique across requests within the same process. Multiple concurrent requests to the same skill get identical audit IDs.",
        "impact": "Cannot correlate logs to specific requests; SK-SYS-AUDIT correlation breaks.",
        "fix": "Include a UUID4 or monotonic counter: `f'audit-{request.skill_id}-{os.getpid()}-{uuid4().hex[:8]}'`",
        "tag": "[OBS]"
      },
      {
        "severity": "LOW",
        "location": "Cognitive contract: PROFILE.md loading order",
        "issue": "TOOL.md is loaded in every instruction stack (`_load_instruction_stack`), but TOOL.md spec says 'Loaded on first tool invocation.' Loading it unconditionally on every request contradicts the contract and inflates token count.",
        "impact": "Wasted input tokens on every request; contract violation.",
        "fix": "Conditionally include TOOL.md only when the skill config declares tool usage, or on first invocation per session.",
        "tag": "[OBS]"
      }
    ],
    "open_questions": [
      "What is the BaseAdapter interface contract? The `execute` method's return dict shape is undocumented and untyped, making the KeyError findings above systemic rather than isolated.",
      "Is `execute_chain` intended for production use? It has no test coverage indicators, no timeout/cancellation, and no max chain length guard (infinite loop risk if planner returns circular capabilities).",
      "Does `validate_output` handle the case where `output` is not a dict (e.g., when JSON parsing succeeds and returns a list)? The `isinstance(output, dict)` guard silently drops validation metadata for list outputs."
    ],
    "test_gaps": [
      "No test coverage for failover path when first adapter succeeds but returns malformed result dict (missing keys).",
      "No test for execute_chain with cognitive_state_override verifying no state pollution across chain steps.",
      "No test for JSON stripping edge cases (nested fences, trailing content after closing fence, non-JSON content starting with `{`).",
      "No test for resolve_alias returning (None, alias) and its downstream effect on the failover loop.",
      "No test for concurrent requests verifying audit_id uniqueness.",
      "No integration test for circuit breaker interaction with cognitive pipeline (breaker open + crash mode)."
    ],
    "summary": "Two critical findings: unguarded dict key access on adapter results silently corrupts the failover chain, and in-place mutation of request.options causes state pollution across chained/retried requests. Six high-severity issues including duplicate code in execute_chain, fragile JSON stripping, silent skill discovery failures, and a backoff mechanism that breaks JSON output. Typing is insufficient throughout; the adapter response boundary is the highest-leverage place to add types. Instruction stack loading contradicts TOOL.md's 'first invocation' contract and lacks caching."
  }
}
