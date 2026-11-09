# Tasks: Personalized Job Ratings

**Input**: Design documents in `/specs/002-personalized-job-ratings/`: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

**Prerequisites**: Existing feature 001 implementation and `.specify/memory/constitution.md` v1.1.0. No new dependency, authentication integration, storage service, or installation mode.

**Tests**: The specification explicitly requires golden validation (FR-012, SC-002–SC-007); the plan requires unit/contract checks, recorded CLI tests, and 90% combined statement/branch coverage. Write meaningful deterministic tests first and confirm the relevant failure before implementing. Live inference and owner semantic review are separate acceptance work.

**Organization**: Setup → shared foundation → US1 (P1) → US2 (P2) → US3 (P3) → cross-cutting acceptance. Markers track completed implementation and deterministic checks. Owner/live/recording-dependent acceptance remains unchecked.

## Format: `[ID] [P?] [Story] Description`

- `[P]` means tasks may run together within the explicitly stated dependency window, on separate files. It does not waive earlier prerequisites.
- `[US1]`, `[US2]`, and `[US3]` map to the stories in `spec.md`.
- Paths are relative to the repository root. Extend existing modules rather than replacing feature 001.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the existing locked environment, replay facilities, and acceptance map.

- [X] T001 Verify `pyproject.toml`, `uv.lock`, and `.python-version` with `uv sync --locked`; retain Python 3.14, exact existing dependency pins, Ruff selections `E,F,W,I,UP,B,SIM,C4,ANN,S,RET,ARG,PTH,RUF`, ty `all = error`, strict generic narrowing/equality, warnings-as-errors, and 90% branch coverage; record baseline check results in `specs/002-personalized-job-ratings/quickstart.md` without upgrading dependencies.
- [X] T002 Extend `tests/conftest.py` with fictional profile/fixed-rating builders and ordered multi-stage HTTP replay helpers that match method, URL, and request-body hash, consume all exchanges, and retain socket blocking and the existing synthetic credential fixture; never mock internal validation/aggregation/rendering for system tests.
- [X] T003 [P] Extend `evaluations/coverage.md` with a feature-002 FR-001–FR-015 / SC-001–SC-008 matrix identifying planned posting/profile pairs, deterministic checks, recording needs, and pending owner review while preserving feature-001 coverage and approvals as historical records.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Strict shared contracts and reusable transport. Complete this phase before any story implementation.

- [X] T004 [P] Add table-driven profile contract tests in `tests/unit/test_profiles.py` for version/root/dimension coverage, strict importance types, absent/blank preferences, absent/empty exceptions, unknown/duplicate TOML definitions, exception ID/kind/excerpt validation, and rejection of declarations without valid preference text; use `contracts/profile.example.toml` as a valid fictional sample.
- [X] T005 Implement pure TOML parsing and strict profile models in `src/job_scan/profiles.py` using `tomllib` and the existing strict Pydantic base; preserve the data-model constraints verbatim: Profile — "Exactly the four supported new IDs in version 1; no extra root fields"; DimensionProfile — "Weight 1–5 controls weighting only; no coercion from booleans, floats, or strings; preferences default to empty and absent/blank prose skips the dimension; exceptions independently default to empty for every dimension; at least one dimension has nonblank preferences; every supplied valid declaration is evaluated"; ExceptionDeclaration — "IDs unique across profile, match `[a-z][a-z0-9_-]{0,63}`; nonblank quote must be an exact contiguous substring of that dimension's preferences; no duplicate `(kind, preference_quote)` in a dimension"; `schema_version` is strict integer 1, `kind` is `compelling_attraction | deal_breaker`, and unknown fields are forbidden. Return safe field/reason diagnostics without rejected values.
- [X] T006 [P] Add response/local-model contract tests in `tests/unit/test_rating_models.py` for strict integers, required nullable fields, nonblank text, rated/insufficient shapes, finding/judgment references, exception states, forbidden model-supplied weights/outcomes, and provider JSON-schema generation; distinguish model-local invariants from request-context validation implemented in stories.
- [X] T007 Define fit, exception, dimension, aggregate, decisive, and composite types in `src/job_scan/rating_models.py`, reusing `Evidence`, `Conflict`, and the existing `Assessment`; quote/enforce DimensionFit invariants "`status` is `rated` or `insufficient_evidence`; explanation nonblank; all fields required in provider response"; SourceFinding "ID unique within dimension; statement nonblank; at least one valid source quote; factual assertions belong here"; PreferenceJudgment "Quote is exact substring of requested dimension prose; finding IDs exist in that dimension and list is nonempty; explanation nonblank; expresses inference rather than an additional unsupported fact", with `polarity: match | mismatch | mixed`; Conflict "Preserve existing requirement for at least two supporting passages; retain conflicting context". Enforce "For `rated`, score is a strict integer from 0 through 100, with at least one source finding and preference judgment" and "For `insufficient_evidence`, score is null and at least one uncertainty or conflict explains why". ExceptionMatch requires `exception_id`, `status: matched | not_matched | unresolved`, nonblank explanation, and evidence; "Matched/not-matched claims require at least one supporting quote". Local state includes `not_configured`; "Entries without preferences retain their declared importance, have null score and no computed findings, and are excluded from aggregation; declarations without valid preference excerpts fail profile validation". WeightedOverall has `status: available | partial | unavailable`, nullable integer numerator/denominator, nullable Decimal value, missing dimension IDs, rated/configured dimension counts, rated/total configured importance, and contributions; "If some configured dimensions are unrated, calculate over rated configured dimensions and label the result partial with all missing dimensions/reasons and coverage; if none is rated, numerator, denominator, and value are null and contributions are empty." Decisive codes are exactly `conflicting_exceptions`, `worth_pursuing_despite_weaknesses`, `deal_breaker`, `unresolved_exceptions`, `no_exception_applies`; retain matched/unresolved IDs and per-pass requested/returned model/configuration metadata.
- [X] T008 [P] Extend `tests/unit/test_ai.py` with legacy request-byte regression checks and typed-request transport tests for completed streams, refusal/incomplete/error events, auth-registration changes, deadlines, malformed schema output, requested/returned model tracking, `store: false`, and safe failures without raw response bodies.
- [X] T009 Extract a small typed structured-request helper in `src/job_scan/ai.py` accepting instructions, serialized user data, schema name, and result type; keep `request_body()` and `assess_html()` byte-compatible with existing recordings, preserve stream-completion and registration/token gating, low reasoning, selected model, 180-second total deadline and 10-second connect timeout, no retry/fallback, and reset returned-model state for each pass.

**Checkpoint**: Shared types/parser and legacy-compatible transport are ready. Story implementations can start; the initial no-declaration MVP is not full feature acceptance.

## Phase 3: User Story 1 — Rate a posting against my written preferences (Priority: P1) — MVP

**Goal**: Read one reusable profile and produce four evidence-backed subjective outcomes alongside unchanged work arrangement. The first runnable increment uses profiles without exception declarations; US2 completes the optional exception stage. Shared profile contracts already validate all declaration syntax.

**Independent Test**: Assess the same authored HTML with contrasting profiles without supplied declarations; verify preserved facts, profile-sensitive role/technology/field/company judgments, exact source/preference references, five identified dimensions, local profile identity, and no cross-invocation profile leakage. A complete fixed-result case also exposes a verifiable weighted mean.

### Tests for User Story 1

- [X] T010 [P] [US1] Add fit request-contract tests in `tests/unit/test_rating_requests.py` for intact HTML, definition-order configured IDs/prose only, omitted paths/hash/source URL/weights/exception metadata/blank preference text, relevant criterion instructions, strict response schema, and byte-identical scoring requests under weight-only or declaration-only changes.
- [X] T011 [P] [US1] Add pure assembly tests in `tests/unit/test_ratings.py` for exact configured-ID coverage, reordered responses, unknown/duplicate/missing/not_configured IDs, exact preference excerpts, dimension-local finding references, raw HTML quote/overlapping-occurrence resolution, evidence deduplication, and basic complete/not_configured/partial/unavailable aggregation and coverage without exceptions.
- [X] T012 [P] [US1] Add personalized rendering tests in `tests/unit/test_personalized_report.py` separating posting facts, preference excerpts, and inferred fit; check named five-dimension output, subjective scale, profile/model identity, auditable mean, “not configured” labels, no-declaration outcome, and terminal-control sanitization without dumping the full profile.

### Implementation for User Story 1

- [X] T013 [P] [US1] Add role policy and versioned prompt fragment in `src/job_scan/criteria/role_fit.py` for responsibilities, seniority, hands-on versus management work, and career direction grounded only in supplied target-role HTML and preference prose.
- [X] T014 [P] [US1] Add technology policy and versioned prompt fragment in `src/job_scan/criteria/technology_fit.py` distinguishing known, desired, avoided, and willingness-to-learn technologies; prohibit familiarity-as-preference and omission-as-absence conclusions.
- [X] T015 [P] [US1] Add field policy and versioned prompt fragment in `src/job_scan/criteria/field_interest.py` for employer business-domain interest, keeping agency/client fields distinct and rejecting model-memory facts inferred from a company name.
- [X] T016 [P] [US1] Add affinity policy and versioned prompt fragment in `src/job_scan/criteria/company_affinity.py` for evidenced employer identity/practices and explicit named-company preferences; distinguish profile beliefs from verified facts and field interest from affinity.
- [X] T017 [US1] Define the static ordered `DimensionDefinition` collection in `src/job_scan/criteria/__init__.py` after T013–T016, with "Static code-owned definitions, ordered presentation; no runtime plugin loading"; preserve separate `work_arrangement` policy and avoid a permanent four/five-element assumption in shared mechanics.
- [X] T018 [US1] Implement deterministic fit projection in `src/job_scan/profiles.py` after T017 as `{html, dimensions: [{dimension_id, preferences}]}` in definition order with configured prose intact; exclude weights, declarations, path/hash, provenance URL, and blank preference content, and preserve serialization under metadata-only edits.
- [X] T019 [US1] Add fit request construction and typed inference entry point in `src/job_scan/ai.py` after T018, composing shared source-only/evidence/uncertainty/untrusted-input instructions with configured criterion fragments and using the helper from T009; no external company lookup or extra request per dimension.
- [X] T020 [US1] Implement pure fit validation and personalized assembly in `src/job_scan/ratings.py` after T019: exact response coverage, request-relative preference/finding validation, existing `resolve()` with "zero-based `occurrence`, counting overlapping matches" and deduplication "by `(quote, occurrence)`", entries without preferences, Decimal weighted means over rated configured dimensions, explicit partial status and dimension-count/importance coverage when some are unrated, unavailable aggregate when none is rated, and local empty/no-exception outcome; retain the original qualitative `Assessment` unchanged and iterate dimension collections. Use integer numerator/denominator, unrounded contributions, and display-only half-up rounding; never include work arrangement.
- [X] T021 [US1] Add a separate personalized renderer in `src/job_scan/report.py` after T020, preserving `render()`; show work findings, all four added outcomes, relevant excerpts/source locations, weights and `importance * score`, denominator and approximate contributions, complete/partial subjective total, coverage and every missing dimension/reason, or unavailable total when none is rated, no-exception state, profile identity, and requested/returned models per pass; apply `safe()` to the complete rendered result.
- [X] T022 [US1] Add `--profile` and bounded local loading in `src/job_scan/cli.py` after T021: profile "Read once per invocation; no mutation; path/hash remain local"; accept UTF-8/BOM regular readable files of 1–65,536 bytes, hash original bytes, reject empty/oversized/non-UTF-8 input without truncation, validate posting and profile before constructing auth/network clients, and resolve paths from invocation directory. For no-declaration profiles run unchanged work stage then fit stage sequentially, assemble and print once; keep no-profile dispatch unchanged. Complete declaration-bearing dispatch in T036 before claiming feature completion.
- [X] T023 [P] [US1] Ship the intentionally incomplete weight-1/empty `examples/preferences.toml` and update `README.md` with `uv run --locked` profile usage, each dimension, known versus desired technologies, 1–5 weighting and blank-preference skipping, explicit excerpt-based exception examples, user replacement instructions, relevant-text transmission, and profile immutability; distinguish comments/placeholders from actual preferences.
- [X] T024 [P] [US1] Manually author fictional contrasting profiles in `evaluations/profiles/` and pair-specific `posting.html`, `metadata.json`, and `expected.json` under `evaluations/personalized/role-contrast/`, `technology-contrast/`, `field-contrast/`, and `affinity-contrast/`; include at least one contrasting pair per new dimension, known/desired/avoided technology, separate field/affinity judgments, exact source/preference excerpts, hashes, prohibited conclusions, and pending review markers. Reuse HTML where justified and never generate expected judgments from inference.
- [X] T025 [P] [US1] Extend `tests/unit/test_evaluations.py` for manifest-v2 per-entry mode dispatch, preserved legacy IDs/expectations, unique required pair IDs, required/null profile rules, strict expectation fields and explicit unknown assertions, complete-suite readiness without auth/network, and no second manifest/path/mode-filter option.
- [X] T026 [US1] Extend `evaluations/run.py` and migrate `evaluations/manifest.json` after T024–T025 to one automatically loaded `schema_version: 2` required list with exact entry fields `id`, `mode`, `posting`, `profile`, `expectations`; preserve baseline posting-path IDs/corpus/request bytes and support repeated postings with distinct pair IDs. Add strict personalized expectations, hash/review/evidence/profile/coverage readiness, per-mode full-suite live dispatch through real components, state/evidence/optional broad-band or relative-direction checks, and per-pass results/models/reasoning/timing/prompt/schema metadata; preserve existing command shape and acceptance-only exit 0. Treat missing annotations as not evaluated, not evidence of absence.
- [X] T027 [US1] Add recorded no-declaration personalized CLI paths in `tests/system/test_personalized_cli.py` and adapt `tests/system/test_recorded_success.py` to typed manifest entries after T026; assert real parser/transport/validation/assembly/rendering, two ordered requests, valid contrasting outcomes, original no-profile replay, and no profile leakage across invocations. Use actual sanitized fictional inference cassettes from T054; missing recordings fail explicitly rather than silently skipping or using synthetic successes.

**Checkpoint**: No-declaration profiles provide the scoring MVP. Golden semantic acceptance and full declaration support remain required work.

## Phase 4: User Story 2 — Make the overall rating reflect my priorities (Priority: P2)

**Goal**: Prove priority weighting and add evidence-backed exceptional outcomes through a separate pass that cannot alter ordinary scoring input or arithmetic.

**Independent Test**: Hold dimension results fixed; check equal, unequal, reversed technology/field, skipped empty preferences, and increased above-average weights, Decimal half-up boundaries, and unrounded contributions. Exercise every decisive outcome, including simultaneous matched types within/across dimensions, unresolved entries alongside confirmed matches, and low-weight cases and absent/empty declaration arrays; verify byte-identical scoring requests for metadata-only changes.

### Tests for User Story 2

- [X] T028 [P] [US2] Extend `tests/unit/test_ratings.py` with fixed-result weighting cases for equal/unequal/reversed weights and skipped empty preferences, above-average monotonicity, integer numerator/denominator, non-terminating Decimal division and half-up one-decimal ties, independently rounded approximate contributions, partial aggregates with a rated-only weight denominator, missing-dimension/coverage disclosure, unavailable aggregates when none is rated, and weighted-score invariance under declaration-only edits.
- [X] T029 [P] [US2] Add `tests/unit/test_exceptions.py` covering all five outcome-table rows from `data-model.md`, same/across-dimension opposing matches, low-weight decisive matches, absent/empty declaration arrays and invalid excerpt references, unresolved entries with either/both confirmed kinds, matched/not-matched quote requirements, absent/duplicate/unknown declaration IDs, invalid evidence, and rejection of model-supplied kind/weight/outcome.
- [X] T030 [P] [US2] Extend `tests/unit/test_rating_requests.py` for supplied-declaration-only exception payloads, no numeric scores/weights/profile paths, exact declaration coverage, no third request when declarations are absent/empty, unchanged fit bytes after kind/add/remove edits, and unchanged fit input after any valid weight edit and changed fit input when preferences become blank.
- [X] T031 [P] [US2] Extend `tests/unit/test_personalized_report.py` with each decisive code, all evaluated declaration statuses/types/excerpts/evidence, both sides of conflicts with no automatic winner, unresolved conditions alongside confirmed-match labels, outcomes with partial/unavailable totals, and unchanged numeric display for declaration-only edits with fixed/replayed dimension results and unchanged weights; do not assert equal live scores or equal weighted totals after weight edits.

### Implementation for User Story 2

- [X] T032 [US2] Add deterministic exception projection in `src/job_scan/profiles.py` as `{html, exceptions: [{dimension_id, exception_id, kind, preference_quote}]}` for supplied declarations only, with no weights/numeric scores; retain locally authoritative declaration types and exact quotes, and leave ordinary fit projection unchanged.
- [X] T033 [US2] Add versioned exception-matching instructions and typed request entry point in `src/job_scan/ai.py` after T032, using the same transport deadline/configuration; require matched/not_matched/unresolved evidence-backed applicability, treat posting omission as unknown, avoid ordinary-score input, and skip the pass entirely for no supplied declarations.
- [X] T034 [US2] Implement contextual exception validation/resolution in `src/job_scan/ratings.py` after T033: "exactly one result per requested declaration and no extras", local profile authority, quote validation even for unresolved entries, and explicit uncertainty for unresolved evidence; reject unsupported shapes rather than interpreting malformed output as unknown.
- [X] T035 [US2] Implement the pure decisive reducer in `src/job_scan/ratings.py` after T034 using all five `data-model.md` table outcomes and local declaration kinds; confirmed opposing matches always yield `conflicting_exceptions`, irrespective of weight/dimension; retain matched/unresolved IDs and evidence, allow outcomes with partial or unavailable numeric totals, and apply no score bonus/penalty/cap/floor.
- [X] T036 [US2] Complete declaration-bearing orchestration in `src/job_scan/cli.py` and exception rendering in `src/job_scan/report.py` after T035: run work → fit → optional exceptions sequentially, preserve per-pass model metadata, assemble/emit only after all stages validate, display every evaluated condition/type/status/reason/evidence, and keep unresolved conditions visible with confirmed-match-only labeling and no conflict winner. Confirm T028–T031 pass against actual aggregation and rendering.
- [X] T037 [P] [US2] Manually author `evaluations/profiles/` and `evaluations/personalized/exceptions/` fixtures/expectations for attraction despite weak scores, deal-breaker despite strong scores, ordinary undeclared prose, unresolved-only and unresolved-plus-matches, same/across-dimension opposing matches, low weights and absent/empty declaration arrays, and partial and unavailable totals with supported exceptions; register every required pair in `evaluations/manifest.json` and map to SC-003/SC-007 in `evaluations/coverage.md`; keep unreviewed content/expectations pending.
- [X] T038 [P] [US2] Extend `tests/system/test_personalized_cli.py` after T036 with actual-response replay for three-stage conflicting exceptions and blank-preference/no-declaration two-stage paths, checking exact exchange counts, both conflict sides, contribution display, no numeric mutation, and complete stdout only; obtain cassettes through T054, never fabricate successful provider provenance.
- [X] T039 [US2] Extend personalized automatic checks and coverage readiness in `evaluations/run.py` and `tests/unit/test_evaluations.py` after T037 to evaluate expected declaration status/aggregate availability/decisive code, score-band/contrast assertions when supplied, and metadata-only request invariants; reject unknown expectation/declaration IDs, missing mandatory exception coverage, and partial-suite acceptance without treating semantic prose matching as an automatic oracle.

**Checkpoint**: Weighting and optional exceptions operate end to end; metadata-only edits leave fit request bytes and fixed-result arithmetic unchanged. Live scores may vary between requests.

## Phase 5: User Story 3 — Understand gaps and correct profile problems (Priority: P3)

**Goal**: Complete actionable safe errors, explicit missing/conflicting evidence, atomic failures, and legacy compatibility.

**Independent Test**: Exercise malformed/local-invalid profiles before any auth/client construction, insufficient/conflicting facts with exit 0, a partial weighted mean and coverage when some configured dimensions are rated, and no overall numeric rating when none is rated, failures at each request stage with exit 1 and empty stdout, interruption with exit 130, and unchanged no-profile assessment/help/auth workflows.

### Tests for User Story 3

- [X] T040 [P] [US3] Extend `tests/unit/test_cli.py` for profile missing/unreadable/nonregular/empty/BOM/invalid UTF-8/64-KiB boundary/oversized inputs, malformed duplicate TOML keys/tables, unknown keys/version, invalid preference types/importance/declarations (including declarations without preference text), source-URL provenance, one read/no rewrite, path identity, safe line/column diagnostics, and proof no auth/network client is constructed on invalid local inputs.
- [X] T041 [P] [US3] Extend `tests/unit/test_rating_models.py` and `tests/unit/test_ratings.py` for all-configured-unknown, supported partial findings with remaining uncertainty under FR-006 (rated and insufficient shapes for the paired US3 scenario-2 examples; semantic sufficiency remains golden-review work), unresolved conflicts, unrated null scores, quote checks on unrated/unresolved results, exact ID coverage failures, and exclusion of qualitative work findings from every numeric aggregate.
- [X] T042 [P] [US3] Add stage-failure/interruption tests in `tests/system/test_personalized_failures.py` using clearly labeled synthetic HTTP error/refusal/incomplete/schema/quote fixtures for work, fit, and exception stages; test absent/ambiguous posting stops later requests, registration changes, timeouts, safe stderr/no partial stdout, and exits 2/1/130 versus successful unknown exit 0.

### Implementation for User Story 3

- [X] T043 [US3] Harden `src/job_scan/profiles.py` and profile loading in `src/job_scan/cli.py` against every T040 boundary, preserving original-byte hashes and configured prose, validating entries without preferences, reporting safe path/field/reason and TOML line/column without document/input dumps, and preventing local-invalid input from reaching auth or network setup.
- [X] T044 [US3] Complete uncertainty/conflict validation and assembly in `src/job_scan/ratings.py` against T041: unknown facts never become zero/mismatch, every supplied quote is resolved, partial aggregate uses rated configured dimensions only with valid numerator/denominator/value/contributions and missing-dimension/coverage disclosure; unavailable aggregate has null numerator/denominator/value, no contributions, and all missing dimensions, and exception outcomes never resolve unrelated missing facts.
- [X] T045 [US3] Complete unknown/conflict presentation in `src/job_scan/report.py` after T044 with supported versus unassessed preferences, all missing dimensions and uncertainties, relevant evidence/conflicting context, clearly labeled partial overall score with dimension-count/importance coverage, no numeric overall score when none is rated, separate unresolved applicability, and sanitization of every source/profile/model-derived value; extend `tests/unit/test_personalized_report.py` for these boundaries.
- [X] T046 [US3] Complete safe atomic failure/exit handling in `src/job_scan/cli.py` and `src/job_scan/ai.py` against T042 after T043–T045; retain original 0/2/1/130 meanings, do not print provider bodies/Pydantic input values/credentials/profile prose on failure, and preserve legacy no-profile request/render/auth/model behavior with no retry or billing fallback.
- [X] T047 [P] [US3] Manually author adverse golden pairs under `evaluations/personalized/evidence-gaps/`, `evaluations/personalized/attribution/`, `evaluations/personalized/structure/`, and `evaluations/personalized/untrusted/` with missing/contradictory/all-unknown facts, partial preferences covering both US3 scenario-2 sufficiency examples with expected rated versus insufficient states, employer versus recruiter/client identity/field, company-name beliefs, omitted technology, structural associations, and embedded instruction attempts; add reviewed-hash fields, required/prohibited expectations, pending statuses, required manifest entries, and coverage mappings in `evaluations/manifest.json` and `evaluations/coverage.md`.
- [X] T048 [P] [US3] Extend `tests/unit/test_evaluations.py` with review-binding regressions for profile/posting/expectation/metadata/manifest/code/lockfile/prompt/schema changes, mismatched run IDs, duplicate/missing/extra required review IDs, pending reviews, stale runs, and complete two-mode suite review; prove review/readiness paths never infer or authenticate and accepted baseline reviews are not transplanted to new runs.
- [X] T049 [US3] Finish immutable run/review binding in `evaluations/run.py` after T048: hash original posting/profile bytes, schema version, expectations/metadata/single manifest/required IDs and modes, code/lockfile, effective prompts/schemas, per-pass requested/returned model/reasoning/timing, automatic results and rendered reports; revalidate current hashes and exact complete case-ID coverage before applying all existing owner review booleans. Store reports only under ignored `.local/evaluations/`; stale/pending/not-evaluated work cannot establish acceptance.
- [X] T050 [US3] Extend `tests/system/test_personalized_cli.py`, `tests/system/test_cli.py`, and `tests/system/test_entrypoint.py` after T046/T049 with actual replay of successful insufficient-evidence reports, partial means and dimension-count/importance coverage when some dimensions are rated, all missing dimensions and no aggregate when none is rated, unchanged legacy/auth/help entry points and `--profile` help, supplied-profile identity across successive invocations, and no extra unrecorded sockets; successful new paths use T054 cassettes.

**Checkpoint**: All three stories have independent deterministic checks and full CLI behavior. Offline checks, genuine corpus reviews, fresh live evaluation, bound owner review, and convergence remain acceptance gates.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Complete documentation and reproducible full-suite acceptance. Do not mark owner-dependent tasks complete without actual owner input.

- [X] T051 [P] Finalize `README.md`, `evaluations/README.md`, and `tests/recordings/README.md` for five-dimension reporting, subjective scale, partial/unavailable totals, separate exceptions, source-only facts, relevant-prose privacy, 360/540-second inference budgets excluding auth, no retry, one manifest/run/review, ignored evaluation outputs, and sanitized actual-versus-synthetic recording provenance; retain all officially supported commands as `uv run --locked`.
- [X] T052 [P] Reconcile `evaluations/coverage.md` against every FR/SC and `specs/002-personalized-job-ratings/quickstart.md` scenario, listing exact required pair IDs and automated test paths; verify all four contrasting groups, all outcome/uncertainty combinations, stage failures, baseline regressions, and request invariants are covered without inferring semantic acceptance from coverage.
- [X] T053 Obtain actual owner source/expectation review for newly authored fictional corpus files and record it in `evaluations/personalized/**/metadata.json` and `expected.json`; do not self-approve owner fields. Run offline unit/contract checks and `uv run --locked python evaluations/run.py --check --output .local/evaluations/readiness.json`, resolving pending/stale/missing coverage before live inference. Readiness is not live acceptance; preserve the contract's exit 1 until an accepted review exists, inspecting the readiness results rather than changing exit semantics.
- [X] T054 Intentionally run the complete mixed-mode live suite with `uv run --locked python evaluations/run.py --live --recordings-dir tests/recordings/inference --output .local/evaluations/latest.json` after T053 using the selected existing model/configuration and actual authenticated transport; capture sanitized actual fictional work/fit/exception SSE by method/URL/request hash for T027/T038/T050, retaining legacy reusable recordings and all required baseline cases. Inspect artifacts for personal data/secrets, preserve provenance, and record failures/variability without generating expectations from results. If auth/allowance is unavailable, retain this task as incomplete and state the dependency.
- [X] T055 Run `uv run --locked ruff check src tests evaluations`, `uv run --locked ruff format --check src tests evaluations`, `uv run --locked ty check src tests evaluations`, and `uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90` after recordings are available; resolve failures and record evidence in `specs/002-personalized-job-ratings/quickstart.md`. Successful replay paths use real internal components and actual sanitized inference; never silently allow live sockets. Changes to bound code/data/configuration require refreshed readiness/live results before T056.
- [X] T056 Obtain one actual owner-authored full-suite review in `.local/evaluations/manual-review.json` bound to the current `.local/evaluations/latest.json` run ID and every required case ID; review semantic correctness, evidence attribution/relevance, required/prohibited judgments, contrasting-profile behavior, unknown states, exception independence/conflicts, baseline regressions, and report usability. Apply it with `uv run --locked python evaluations/run.py --review .local/evaluations/latest.json --manual-review .local/evaluations/manual-review.json --output .local/evaluations/reviewed.json`; require all mandatory checks and `accepted=true`, record model/configuration and variability limitations, and never fabricate or copy old approval.
- [X] T057 Execute the starter-edit/help/no-profile/personalized/privacy scenarios in `specs/002-personalized-job-ratings/quickstart.md` and record actual results there, using ignored `.local/preferences.toml` for personal edits and confirming unchanged input bytes; use fictional profiles for any newly versioned artifacts. Keep missing live/owner acceptance explicit and rerun affected checks/reviews if code or evaluation inputs change.
- [X] T058 Run `$speckit-converge` against `specs/002-personalized-job-ratings/spec.md`, `plan.md`, this `tasks.md`, and the implemented code after T055–T057; append and finish any remaining required work, record the final constitution review and validation/acceptance references in `specs/002-personalized-job-ratings/quickstart.md`, and claim feature completion only when required checks, current full-suite owner acceptance, and convergence all pass.

## Dependencies & Execution Order

### Phase dependencies

```text
Setup T001–T003
  → Foundation T004–T009
    → US1 T010–T027 (no-declaration scoring MVP)
      → US2 T028–T039 (weighting verification and optional exceptions)
        → US3 T040–T050 (uncertainty, errors, compatibility, review binding)
          → Acceptance T051–T058

Corpus authoring T024/T037/T047 + runner T026/T039/T049
  → owner content/expectation review + readiness T053
    → live recording T054 → recorded system checks + offline gates T055
      → bound full-suite owner review T056 → quickstart T057 → convergence T058
```

- T001 precedes the test infrastructure work; T002 and T003 can then run together.
- Foundation test files T004/T006/T008 can be written together; T005, T007, and T009 follow their respective failing tests. Shared infrastructure is a prerequisite for all story implementation.
- US2 depends on US1's scored results, projection, CLI, and renderer. US3 completes robustness across both previous stories. These are genuine feature dependencies; do not treat the three end-to-end implementations as independent branches.
- US1's complete no-declaration path already calculates the contract's weighted mean and displays no-exception state. US2 adds adversarial arithmetic coverage and the actual exception stage; it does not redefine the mean.
- Corpus authoring can proceed independently after foundation using design contracts, but serialize edits to shared `evaluations/manifest.json` and `evaluations/coverage.md` across T024/T037/T047. T025 precedes T026; T037 precedes T039; T048 precedes T049.
- T027/T038/T050 define recorded system paths before recording capture; those new success checks cannot pass until T054 supplies actual cassettes. Run their deterministic/unit prerequisites before live capture, and the complete required offline gates afterward. Do not manufacture a recording to unblock a checkpoint.
- T053 and T056 need actual owner reviews; unavailable owner input or live credentials is an explicit outstanding dependency, not permission to approve automatically or claim completion.
- T054 produces the candidate immutable run. Any subsequent bound-code, profile, corpus, manifest, prompt/schema, or lockfile changes invalidate it and require a fresh readiness/live run and review. Documentation-only progress notes do not justify unnecessary re-inference.

### Within each story

Write tests and establish relevant failures → models/contextual validation → pure policy/services → request/CLI integration → recorded independent verification. Existing contracts are required throughout; later failure-hardening tasks do not authorize fabricated facts, partial successful reports, or unvalidated data in earlier increments.

## Parallel Execution Examples

### User Story 1

After foundation, write T010 (`test_rating_requests.py`), T011 (`test_ratings.py`), and T012 (`test_personalized_report.py`) together. Independently implement T013/T014/T015/T016 in the four separate criterion modules, then join at T017. T023 documentation/starter and T024 corpus authoring can proceed alongside scoring implementation while avoiding edits to shared coverage files. T025 runner tests can run alongside those tasks; T026 waits for its tests and corpus.

### User Story 2

After US1, write T028 arithmetic tests, T029 exception tests, T030 request tests, and T031 report tests concurrently in their separate files. Run T037 corpus work alongside T032–T036 exception implementation; serialize manifest/coverage edits. After T036, T038 system tests and T039 runner checks can proceed together because they edit distinct files.

### User Story 3

After US2, write T040 local-input tests, T041 model/pure-result tests, and T042 system failure tests together. T047 adverse corpus authoring and T048 review-binding tests can run alongside robustness implementation. T043 and T044 may proceed together (CLI/profiles versus pure ratings); T045 follows T044 and T046 follows both. T049 evaluation binding can proceed alongside report/CLI hardening after T048.

### Cross-cutting

T051 documentation and T052 coverage reconciliation use separate files and can proceed together once story behavior is settled. Owner review, readiness, live capture, final gates, and bound acceptance follow the dependency chain above; do not parallelize mutations to the same artifacts or acceptance against changing hashes.

## Implementation Strategy

### MVP first

Complete setup/foundation and US1 with no exceptional declarations. Validate the four criterion interpretations against contrasting fictional profiles, intact evidence, a fixed-result weighted example, and preserved work arrangement. This is the smallest usable scoring increment; it is not acceptance of the complete exception-capable feature. Actual replay and semantic owner review still apply before any acceptance claim.

### Incremental delivery

Add US2's independent exception pass and prove numeric/input invariants. Add US3's adverse-input, uncertainty, atomic-failure, legacy, and review-binding behavior. Then complete current-hash full-suite validation and owner acceptance. Keep criterion-specific policy in separate modules and shared arithmetic/evidence mechanics pure; all filesystem/auth/network effects remain in the imperative shell.

### Verification boundaries

Unit/contract tests establish deterministic schema, evidence-reference, request, weighting, and outcome rules. Recorded CLI tests establish real-component integration with external services replayed and sockets blocked. Opt-in live calls plus actual owner review establish semantic quality and usability. None substitutes for the others. Future dimensions require explicit code/contracts rather than dynamic plugins or a fixed product-wide dimension count.


## Execution checkpoint — 2026-11-09

48/58 tasks are marked complete. Implementation and deterministic checks are present; required
actual-success recordings and owner acceptance are not. Full preliminary validation: 264 passed,
32 missing-cassette failures, 97.85% combined coverage; Ruff lint/format and strict ty pass.
Readiness has 16 ready baseline entries and 31 pending owner source/expectation reviews, with
no missing coverage groups. See quickstart.md for commands and results.

T027/T038/T050 replay tests are authored and fail explicitly until T054. T042's synthetic failure
matrix passes; its comparison with successful unknown exit-0 paths remains pending with T050.
T053 is the next external dependency: actual owner review of the linked fictional source/profile
expectations in evaluations/personalized/README.md. T054–T058 and feature acceptance remain open.


Owner source/expectation approval received (“looks good”); all 47 cases are ready with no coverage issues. T053 is complete. Live capture and bound semantic acceptance remain separate.


T054 attempt after approval: the full 47-case suite failed before inference because the
saved session could not be refreshed and requires sign-in. No new recordings were captured.
An encrypted transfer recipient is prepared; fresh authentication is the next dependency.
T054 remains unchecked, and final acceptance/convergence are not claimed.


## Accepted validation before final convergence

The final complete run `b1d1383f7a6856baf98353aa9b9133bc0455ead4951eb5bf26d732eb31aa0486` passed all 47 automatic checks
with `gpt-6.1-sol`, low reasoning, and 89 completed stages. All 64 distinct current
request cassettes are available; 11 superseded untracked development recordings were moved
to ignored `.local/evaluations/superseded-recordings/`. Recording hygiene checks passed.
All 298 socket-blocked tests pass with 98.04% combined coverage; Ruff lint/format and strict
ty pass. Starter-edit, legacy/personalized dispatch, provenance privacy, immutable profile
bytes, and installed help checks pass.

The owner explicitly replied “I reviewed and approve all 47 cases” to the question covering
semantic correctness, evidence relevance, absence of prohibited conclusions and usability
for that exact run. The approval is recorded in `.local/evaluations/manual-review.json`;
review application exited 0 with `accepted=true` in `.local/evaluations/reviewed.json`.
57/58 tasks are now complete; T058 is the remaining final convergence step.


## Final completion

All 58 tasks are complete. Final convergence assessed 15 functional requirements, 8 success
criteria, 21 user-story acceptance scenarios, 14 plan obligations and all 6 constitutional
principles. No missing, partial, contradictory or unrequested gaps were found (zero findings
at every severity); no convergence remediation section was appended. The convergence
command itself left this file unchanged; this completion marker is recorded by implement
after the clean result. All required offline checks and current bound full-suite owner
acceptance pass. See quickstart.md for the final record and limitations.
