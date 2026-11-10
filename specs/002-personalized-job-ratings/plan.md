# Implementation Plan: Personalized Job Ratings

**Branch**: `main` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-personalized-job-ratings/spec.md`, including the confirmed exception outcomes and dimension terminology.

**Status**: Design and implementation are complete. The full live/replay suite, current bound owner semantic review and final convergence pass. See tasks.md and quickstart.md.

## Summary

Add `assess POSTING --profile PROFILE.toml` to evaluate four new dimensions: role fit, technology fit, field interest, and company affinity. Work arrangement remains the existing qualitative fifth dimension. Reuse the existing stack, authenticated transport, source-quote resolution, and terminal workflow. Keep dimension-specific instructions in separate modules; share validation and deterministic arithmetic across a collection of scored results.

Use one user-edited TOML file with explicit 1–5 weights and optional compelling-attraction/deal-breaker declarations referencing existing preference prose. Absent or blank preferences skip a dimension; nonblank preferences are assessed. Importance only weights the mean. There is no enable/disable setting. Every supplied valid declaration is evaluated, while an absent or empty declarations array means none. Preserve the weighted numeric score and calculate a separate decisive outcome, including “conflicting exceptions” when both kinds match. No persistent assessment storage, external company retrieval, dynamic criterion plugins, or new dependency is needed.

## Technical Context

| Item | Design choice |
| --- | --- |
| Language/version | Python `>=3.15.2,<3.16` with exact 3.15.2 pin in `.python-version` (upgraded with owner approval on 2026-11-09); officially supported execution is `uv run --locked` |
| Primary dependencies | Keep `httpx==0.28.1`, `pyjwt[crypto]==2.15.1`, `pydantic==2.14.3`, `typer==0.28.0`; no additions; standard-library `tomllib`, `hashlib`, and `decimal` |
| Development | Keep exact Ruff, ty, pytest, pytest-cov, pytest-socket pins and committed `uv.lock` |
| Storage | One explicitly selected local profile; existing private OAuth registration storage; fictional golden profiles and sanitized recordings in the repository; ignored developer evaluation reports; no assessment database |
| Testing | Pure unit/contract checks, real-component CLI tests with HTTP replay and sockets blocked, separate opt-in live semantic golden evaluation |
| Platform/type | Existing synchronous personal CLI on Linux/macOS; no new installation/platform support |
| Performance goals | Legacy: one request. Personalized: two sequential requests, or three when supplied exceptions exist. Each inference request retains a 180-second total deadline and 10-second connection timeout; max inference budget 360/540 seconds respectively, excluding authentication; no automatic retry |
| Input limits | Existing one UTF-8 HTML file up to 256 KiB, intact; new one UTF-8 TOML regular file up to 64 KiB; fail rather than truncate |
| Model/configuration | Preserve existing `DEFAULT_MODEL`, low reasoning, and `--model` selection; no implicit model substitution or billing fallback; record requested and returned model per pass |
| Scale/scope | One posting/profile pair per invocation; five dimension outputs in this increment, four participating in numeric aggregation; future dimensions added through code and explicit contracts |
| Security/privacy | Validate inputs before creating auth/network clients; do not send paths, weights, blank preference text, or complete file bytes; send relevant preference content only, with `store: false`; no profile dumps in diagnostics |

## Constitution Check

Pre-research gate: **PASS**. The clarified spec has no identified constitutional violation. Post-design gate: **PASS by design**, with the following required implementation/acceptance checks.

| Principle / policy | Design evidence | Gate |
| --- | --- | --- |
| I. Keep it simple | TOML/std-library parsing, existing stack and transport, static criteria definitions, no storage or plugin framework | Pass |
| II. Evidence and explicit uncertainty | Exact HTML quote/occurrence resolution, explicit insufficient/unresolved states, factual/preference/judgment separation, owner evidence-relevance review | Pass (verified) |
| III. Separate criteria | Four dedicated prompt/policy modules; shared mechanics independent of criterion content; existing work-arrangement policy preserved | Pass |
| IV. Development practices | Strict tooling, 90% coverage target, TDD for core rules, imperative file/auth/network shell and pure validation/aggregation/rendering; real-component recorded CLI tests | Pass (verified) |
| V. CLI | Optional profile flag, starter file/guidance, atomic terminal report, preserved errors/exit codes | Pass |
| VI. Golden validation | Manually authored posting/profile pairs, bound owner review, model/configuration and limitations in evaluation reports | Pass (verified with bound owner acceptance) |
| Product boundaries | Saved HTML only; provenance URLs never fetched; supported inputs, output, failures, limits, and exclusions specified | Pass |
| Reproducibility/workflow | Exact existing pins, `uv.lock`, locked commands; tasks and convergence follow planning | Pass |

No amendment, unresolved gate, or complexity exception is required. This review does not certify unimplemented behavior or pending live evaluations.

## Design

### Profile loading and validation

The CLI loads both local inputs before opening `ChatGPTSession` or `ResponsesClient`. Bound file reads reject non-regular, unreadable, oversized, empty, invalid-UTF-8, or malformed input. Parse TOML, then run strict validation with forbidden extras; require version 1 and the four currently supported new dimension keys. Reject invalid weights, booleans masquerading as integers, invalid preference types, all-blank preferences, duplicate definitions/exception IDs, unknown names, and invalid preference excerpt references. Never rewrite the profile.

Starter at `examples/preferences.toml` will contain all four dimensions with importance 1, empty preferences, and explanatory comments; users must enter real prose for at least one dimension. The starter documents that relevant text goes to the model. The completed example in [contracts/profile.example.toml](contracts/profile.example.toml) demonstrates syntax; it is fictional example data, not a user's stored profile.

### Request stages and stable numeric scoring

1. Reuse the original work-arrangement request and source validation unchanged. If the target posting is absent/ambiguous or the request fails, stop with no report.
2. Issue one fit request composed from shared evidence/uncertainty instructions and the configured criteria's separate prompt fragments. Supply intact HTML plus `{dimension_id, preferences}` entries. Do not include weights, exceptional metadata, profile paths, or dimensions without preferences. Validate schema, exact configured-ID coverage, preference excerpts, finding references, and every source quote.
3. If supplied declarations exist, issue a separate exception-applicability request with intact HTML and declared preference excerpts/IDs/types. Validate exact declaration coverage and evidence. This pass sees no numeric results and cannot change them. Skip it when there are no supplied declarations.
4. Assemble entries without preferences locally, calculate the weighted mean and contributions, and reduce matched exception types to a decisive outcome. Render only after every required pass succeeds. An inference failure at any stage fails the entire invocation; an insufficient-evidence result remains a successful assessment.

The transport extraction keeps the original wrapper's instructions, schema, input serialization, timeout, registration checks, and completion gating. A typed reusable helper takes instructions, serialized user data, schema name, and result type; do not build an agent/orchestration framework. All factual input remains the supplied HTML. A source URL is never sent as evidence or fetched.

The plain scoring projection is byte-identical when only importance or exceptional declarations change. A declaration references an exact excerpt already in the dimension's prose, so adding its status cannot introduce new ordinary-scoring content. Underlying preference edits can change the ordinary score. Live stochastic outputs can still vary; do not promise exact cross-run score equality.

### Pure assessment rules and extensibility

Use strict typed fit models, exception models, and a composite personalized assessment containing the existing `Assessment` plus a collection of new dimension outcomes. Keep the original assessment and report unchanged for invocations without a profile. Use stable IDs and iterate scored collections for weighting/rendering. A static ordered list of current criterion definitions is sufficient; no code assumes four is the permanent product total.

Calculate `sum(weight * score) / sum(weight)` over rated configured new dimensions. Show a complete score when all configured dimensions are rated, a clearly labeled partial score when only some are rated, and no numeric score when none is rated. Keep integer numerator/denominator and Decimal division; round half up only at final display to one decimal. Show weight, score, weighted numerator, denominator, and contribution so the result is auditable. Missing data never becomes zero. Exclude its weight from the partial denominator explicitly; show every missing dimension and reason, rated/configured dimension counts, and rated/total configured importance. Work arrangement remains qualitative and excluded.

Exception applicability is `matched`, `not_matched`, or `unresolved`. Use authoritative local declaration types, not model-returned types. The pure outcome reducer implements the table in [data-model.md](data-model.md). Both matched kinds always yield “conflicting exceptions,” regardless of weights or dimension location. Unknown conditions remain visible alongside any confirmed outcome, including when no overall numeric score exists.

### Privacy and failure handling

Use path/field names and safe static reasons in validation errors, with TOML line/column where available. Do not print Pydantic input values, parser document text, HTTP response bodies, profile contents, or credential values. Normal reports include only relevant verified preference excerpts. Apply existing terminal sanitization to every displayed source/profile/model value.

Personalized output may list the actual returned model for each stage. It labels scores subjective, explains partial or unavailable overall scores and unresolved exceptions, and identifies all five dimension outputs. Print no partial report before success. Preserve exit 2 for local input/argument errors, 1 for auth/provider/schema/evidence failures, 130 for interruption, and 0 for successful reports including unknown results.

## Verification and Acceptance

### Required offline gates

Keep Ruff's existing strict selections `E,F,W,I,UP,B,SIM,C4,ANN,S,RET,ARG,PTH,RUF`; retain ty `all = error`, strict generic narrowing/equality, and warnings-as-errors. Keep the combined statement/branch coverage target at **90%** across the application, including existing auth/transport. Run:

```bash
uv run --locked ruff check src tests evaluations
uv run --locked ruff format --check src tests evaluations
uv run --locked ty check src tests evaluations
uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90
```

Prefer TDD for meaningful boundaries: profile coercion/validation, exact result coverage, evidence and preference references, partial/unavailable aggregates and coverage, rounding, and exception reduction. Table-driven pure tests cover all five decisive outcomes, uncertainty coexisting with matches, low-weight conditions and absent/empty declaration arrays, same/across-dimension conflicts, and score invariance under metadata-only changes. Fixed-result examples verify arithmetic and monotonicity; no exact-score live oracle. Apply spec FR-006 and the paired US3 scenario-2 examples to partial evidence within a dimension: require an explanation supporting the dimension-level judgment without assumed facts about unassessed preferences, or retain findings with insufficient evidence. Golden review establishes this semantic boundary; schema checks alone cannot.

A small personalized CLI system matrix covers completed scoring, conflicting exceptions, missing evidence/partial overall score and coverage, all-configured-unknown/no overall score, invalid profile before authentication, dimensions without preferences/no exception request, failure in a later pass/no stdout report, and existing no-profile behavior. Exercise actual parsing, HTTP adapter, validation, aggregation, and rendering. Replay sanitized actual provider inference streams for successful paths; synthetic fixtures may exercise transport/refusal/schema/evidence failures, clearly labeled. Block all unrecorded sockets in ordinary tests. Existing OAuth replay and installed-command help smoke tests remain.

### Golden corpus and live acceptance

Extend `evaluations/run.py` with per-case work-arrangement/personalized modes in one automatically loaded `evaluations/manifest.json`, as specified in [contracts/evaluation.md](contracts/evaluation.md). Migrate existing entries and add the new pairs to that same required list. Keep existing evaluation commands; introduce no manifest-path option. One run and bound owner review cover the full suite. Manually author at least one contrasting-profile pair per new dimension, plus cases for known/desired/avoided tech, field versus employer affinity, recruiter/client attribution, missing/conflicting source facts, structural associations, untrusted instructions, and all exception outcomes. Include exceptional status toggles on unchanged text and changed weights as request-projection checks. Reuse shared HTML where its evidence supports the expectations; add fictional focused postings where it does not.

Run offline readiness before live inference. Live subscription calls are opt-in and use actual transport; auth/catalog and inference are never silently live in routine tests. Record code/data/profile/manifest/expectation/lockfile/prompt/schema hashes, per-pass requested/returned models, reasoning, timing, immutable run ID, automatic results, manual review, and limitations. Capture only sanitized fictional inference exchanges; never record real credentials or personal profile data.

All spec-mandatory golden judgments, states, evidence, and prohibited-conclusion checks must pass. Owner review must actually establish semantic correctness, relevant evidence, contrastive profile behavior, and report usability for every required pair. Evaluate the existing work-arrangement corpus as a regression as well; changed application/evaluation hashes invalidate old review bindings even if its request recordings remain reusable. Acceptance records must describe remaining model variability. Never fabricate owner approval. Corpus authoring and fresh accepted evaluation are implementation deliverables, not prerequisites to generating this design. Convergence follows implementation.

## Project Structure

### Documentation (this feature)

```text
specs/002-personalized-job-ratings/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
    cli.md
    profile.md
    profile.example.toml
    evaluation.md
  checklists/requirements.md
```

`tasks.md` contains the implementation and acceptance tasks generated by `$speckit-tasks`.

### Source Code (repository root; proposed changes)

```text
src/job_scan/
  cli.py                    # --profile and bounded profile-file loading
  ai.py                     # shared typed request mechanism; legacy wrapper preserved
  models.py, evidence.py    # existing source/result types and quote resolution
  profiles.py               # pure profile parsing, validation, score projection
  rating_models.py          # new response and composed result types
  ratings.py                # pure evidence assembly, aggregation, outcome reduction
  report.py                 # preserve render(); add personalized rendering
  criteria/
    work_arrangement.py     # preserved qualitative dimension
    role_fit.py
    technology_fit.py
    field_interest.py
    company_affinity.py
examples/preferences.toml   # documented editable starter
tests/unit/                # profile, rating, request-contract, and report checks
tests/system/              # real CLI replay coverage
tests/recordings/inference/# sanitized actual fictional responses
evaluations/
  run.py                    # preserve legacy mode; add personalized mode
  manifest.json             # one required suite: existing cases plus new profile pairs
  profiles/                 # fictional contrasting profiles
  personalized/             # pair expectations and focused postings as needed
  coverage.md, README.md
```

**Structure Decision**: Extend the current single Python package. Keep file/auth/network effects in the CLI/transport and deterministic logic in ordinary functions. New dimensions require dedicated criterion code and explicit supported contracts; no dynamic loading or permanent five-dimension cap.

## Complexity Tracking

No constitutional violations or exceptions. The optional third model request is justified by the confirmed requirement that exceptional status not alter ordinary numeric scoring. It reuses existing transport and introduces no service or framework.


## Planning Validation

Phase 0 decisions and Phase 1 contracts are complete. Verified all eight generated artifacts, local Markdown links, TOML example syntax/keys/exception references, rejection of invalid weight types under the installed pinned Pydantic version, and Decimal half-up rounding at a boundary using `uv run --locked python`. Post-design constitution gates pass by design. No new code, application test run, live inference, or owner acceptance is claimed. No before/after planning hooks are registered (`.specify/extensions.yml` absent).

Next command: `$speckit-implement`.

Owner refinement: use one automatically loaded evaluation manifest for both assessment modes, one full-suite run, and one bound owner review. The existing evaluation command shape is retained.
