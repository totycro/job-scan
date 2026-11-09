# Research: Personalized Job Ratings

**Date**: 2026-11-09
**Scope**: Resolve the technical choices for feature 002 against the existing implementation. These are design decisions, not implementation or model-validation results.

## 1. Reuse the installed stack and subscription transport

**Decision**: Retain Python 3.14, uv, the exact dependency pins in `pyproject.toml`, and `uv.lock`. Reuse Typer, Pydantic, HTTPX, and the current authenticated Responses transport. No new dependency or billing path is needed.

**Rationale**: `src/job_scan/cli.py` already validates local inputs before authentication; `ai.py` already gates successful output on stream completion, validates schemas, and checks registration changes. Preserve the legacy `request_body`/`assess_html` behavior and request serialization so existing recorded successes remain usable. Extract a typed internal structured-request helper without changing the old wrapper's payload.

**Alternatives considered**: An agent framework, a new SDK, a second authentication integration, and a provider migration add scope without user value. No provider API redesign is required or assumed.

## 2. One TOML profile with explicit exception references

**Decision**: Read UTF-8 TOML using standard-library `tomllib`; validate the parsed mapping with strict Pydantic models and forbidden extra fields. The profile has a version, a required `dimensions` table with four named entries, optional prose preferences, integer importance 1–5 for weighting only, and optional exception declarations. Absent or blank preferences skip a dimension; at least one dimension must have nonblank prose. There is no enable/disable setting. Absent or empty exception arrays mean none; every supplied valid declaration is evaluated. Each declaration identifies an exact excerpt of that dimension's preferences and its exceptional type. An excerpt identifies the underlying preference; it is not an extra scoring instruction.

**Rationale**: Multiline prose, comments, integers, and named tables make a reusable profile readable without a parser dependency. Exception metadata can be added to existing prose without changing the scoring input. The Python documentation specifies the parser and location-bearing errors; size-limit files before parsing. Diagnostics expose field paths and locations, not parser documents or profile values. [Python 3.14 tomllib](https://docs.python.org/3.14/library/tomllib.html).

**Alternatives considered**: YAML adds a dependency and coercion behavior; JSON is less comfortable for long prose/comments; Markdown with a custom header/parser needs more bespoke syntax. Separate profile files and discovery are deferred by the spec. Embedding exceptional status only in prose makes declaration identity and validation ambiguous.

## 3. Separate model scoring from exceptional status

**Decision**: In personalized mode run the unchanged work-arrangement request, then one new fit request for all configured new dimensions. Run one additional exception-matching request only if configured dimensions declare exceptions. Execute sequentially and publish one report after all stages validate. The fit request receives only dimension IDs and preference text, without importance, exception IDs/types, overall outcomes, profile paths, or dimensions without preferences. The exception request receives HTML and the declared preference excerpts with IDs/types, without numeric scores.

**Rationale**: Changing weights or adding an exceptional declaration to unchanged preferences must leave the scoring request byte-identical. The separate pass prevents exception labels from affecting scores by construction. A single fit request avoids one network call per new criterion; separate criterion prompt fragments retain independent ownership. Both new passes use the existing 180-second per-request total deadline and 10-second connection timeout; maximum inference time is 540 seconds with three passes, or 360 seconds without exception evaluation, excluding authentication. Legacy mode remains one request. No retries or parallel network work are introduced.

**Alternatives considered**: One combined request is cheaper but allows exception instructions to influence numeric scoring. Separate calls per dimension make the personal CLI slower and complicate atomic failure handling. Caching scores or adding persistent assessment storage is outside scope. Identical scoring requests do not guarantee identical live model outputs; verify the invariant with request identity and fixed-result tests, and acknowledge model variation.

## 4. Strict evidence-backed results and local derivation

**Decision**: Use `Evidence(quote, occurrence)` and `resolve()` from the current source model. Add typed fit and exception response schemas with IDs and explicit states. Require source evidence for scored dimensions and resolved exception claims; preserve insufficient/conflicting evidence. Validate profile references locally as well as posting quotes. Derive entries without preferences, weighting, and the decisive outcome locally after validation; never accept a model-provided overall score or winner.

**Rationale**: Existing quote provenance works on intact HTML and preserves structural evidence. Strict models and generated schemas already fit the codebase; field and cross-field validators enforce invariants that a schema alone cannot express. Strictness is deliberately used to reject type coercion, and schema generation is distinct from semantic validation. [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/).

**Alternatives considered**: Free-form responses and model-calculated aggregation are harder to verify. Exact quote existence cannot establish entailment; owner review remains mandatory. Unknown facts cannot be replaced with model memory or external research in this feature.

## 5. Growing dimensions without a plugin framework

**Decision**: Give each criterion a stable ID and its own prompt/policy module. Maintain a small static ordered definition list for the four new scored dimensions; include the existing `work_arrangement` as a separately identified qualitative result in the final assessment. Iterate collections in aggregation and rendering instead of positional four-element arithmetic. A future dimension is a code addition and an explicit profile-version/contract change where necessary.

**Rationale**: Five dimensions exist in this increment; only the four additions participate in this profile and numeric aggregation. This follows the constitution's separation rule without requiring runtime criterion loading. Current profile validation deliberately rejects unsupported keys; conceptual extensibility does not imply accepting unknown dimensions now.

**Alternatives considered**: A universal scored base type would force work arrangement into an unsupported numeric model. A fixed total of four contradicts the clarification. A dynamic plugin/registry system is unnecessary.

## 6. Golden evaluation keyed by posting/profile pair

**Decision**: Use one versioned `evaluations/manifest.json` for the full required evaluation suite, loaded automatically by the existing runner. Each entry has a stable ID, assessment mode, posting path, optional profile path, and expectation path. Migrate existing work-arrangement entries while preserving their IDs and corpus; add personalized posting/profile pairs to the same list. One run and one owner review cover both modes; no manifest-path option or separate manifest is needed. Bind reviews to pair ID and hashes of both inputs, expectations, prompts/schemas, code/lockfile, model/configuration, and the immutable run ID.

**Rationale**: `evaluations/run.py` currently hardcodes `work_arrangement` and profile-less case keys in multiple models. Merely adding expected score fields would lose profile identity and permit stale reviews. Shared posting HTML remains reusable across profiles. Author semantic expectations, explicit states, prohibited conclusions, and comparative fit judgments; do not require exact model scores or prose. Use fixed results for arithmetic and decisive-outcome tests.

**Alternatives considered**: Replacing the legacy corpus risks acceptance regressions. Treating provider recordings as golden answers confuses transport replay with semantic correctness. Separate manifests and a manifest-path option add selection overhead and make it easier to omit regressions. A typed mode per case in one required suite is sufficient; full generic evaluation infrastructure is unnecessary.

## Research outcome

All technical choices are resolved. The design uses no new dependency and no constitutional exception. New manually authored corpus annotations, actual recordings, implementation, and owner-bound live review remain future acceptance work; none is claimed complete here.
