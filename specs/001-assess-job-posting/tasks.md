# Tasks: Assess a Job Posting

**Input**: Design documents in `specs/001-assess-job-posting/`.
**Prerequisites**: Owner-approved spec and plan; research.md, data-model.md, contracts/cli.md, quickstart.md, and constitution.
**Status**: Owner-approved on 2026-11-06; three minor analysis findings clarified with owner authorization. Implementation and all required checks pass; the owner approved all updated live reports on 2026-11-06. All 33 tasks complete. The first convergence pass identified one documentation gap, completed as T033; the final pass on 2026-11-06 found zero remaining gaps.
**Maintenance status (2026-11-09)**: Owner-authorized Typer migration completed as T034–T036. All 36 tasks complete; required checks pass with 96 tests and 97.30% combined coverage.

**Tests**: Include deterministic and real-component CLI tests plus live golden evaluation as required by the plan and constitution. Prefer tests first for validation, preferences, and failures; confirm meaningful failures before implementation.
**Organization**: One story exists: US1, “Understand work arrangements from posting HTML” (P1). Authentication is a prerequisite of its selected provider, not an additional product story.

## Format and paths

Each task uses `- [ ] Tnnn [P?] [US1?] Description with file paths`. `[P]` means tasks can proceed independently once their stated prerequisites are met; it does not authorize spawning agents. Paths are relative to the repository root. Keep effects in CLI/auth/transport and pure validation, preferences, and rendering in the core.

## Phase 1: Setup

**Purpose**: Establish the Python package and mandatory development checks.

- [X] T001 Initialize Python 3.14 packaging, argparse entry point, module skeletons, and dependency groups in `pyproject.toml`, `.python-version`, `src/job_scan/__init__.py`, `src/job_scan/cli.py`, and `src/job_scan/criteria/__init__.py`; select HTTPX, PyJWT with crypto, Pydantic 2, Ruff, ty, pytest, pytest-cov, and pytest-socket; resolve versions into `uv.lock` without inventing pins.
- [X] T002 Configure `pyproject.toml` with Ruff rules `E,F,W,I,UP,B,SIM,C4,ANN,S,RET,ARG,PTH,RUF`, Python 3.14 target, 100-character lines, format checks, and tests-only S101 exemption; ty checks `src`, `tests`, `evaluations`, with `all = "error"`, `strict-generic-narrowing = true`, `strict-equality-semantics = true`, and `error-on-warning = true`; enable strict pytest markers and at least 90% combined statement-and-branch coverage over all `job_scan` modules including auth/transport; require annotations and justify any narrow suppression.
- [X] T003 [P] Update `.gitignore` to exclude `.local/`, caches, build artifacts, and local secrets while retaining versioned corpus, sanitized recordings, feature artifacts, and `uv.lock`; preserve existing exclusions.
- [X] T004 Build offline test infrastructure in `tests/conftest.py` and `tests/recordings/README.md`: block unrecorded sockets, inject HTTPX transport, seed synthetic unexpired job-scan sessions, match HTTP method/URL/request-body hash, reject unmatched calls, and document sanitation and deliberately synthetic OAuth fixtures; no production replay flags.

**Checkpoint**: Package/check configuration exists; ordinary tests cannot silently call external services.

## Phase 2: Foundational prerequisites

**Purpose**: Implement the shared response contracts and subscription integration required by US1.

- [X] T005 Specify strict response-model tests in `tests/unit/test_models.py` for `posting_status` values `identified | ambiguous | absent`, arrangement `kind` values `remote | hybrid | onsite`, schedule `kind` values `allowed | expected | unspecified`, nullable schedule strings, required evidence on positive facts/conflicts, multiple alternatives, and empty arrangements; reject unknown keys and type coercion, require null quantity/period for unspecified schedules, and test posting_explanation as a required nullable field: nonempty after trimming for ambiguous/absent status and null for identified.
- [X] T006 Implement strict Pydantic response and assessment types in `src/job_scan/models.py` per `specs/001-assess-job-posting/data-model.md`: “disallow unknown keys and type coercion”; `quote`: “nonempty exact contiguous substring of `html`; markup is permitted”; `occurrence`: “zero-based index among occurrences of that exact substring, counted by increasing start position (including overlapping matches)”; `days_text`/`period`: “nullable strings preserving the stated quantity/range and period”; `unspecified`: “has null quantity/period”; encode evidence/context requirements without fabricating absence quotes; posting_explanation is required nullable text, nonempty after trimming for ambiguous/absent status and null for identified. Satisfy T005.
- [X] T007 [P] Write authentication lifecycle tests in `tests/unit/test_auth.py` and sanitized/synthetic fixtures in `tests/recordings/auth/`: new/returning registrations, PKCE/state/nonce and identity verification, granted/missing plan permission, active selection, expiry/refresh, revoked sessions, storage permissions/atomic writes/locking, login timeout, logout cleanup and unconfirmed revocation, and secret-free diagnostics/status without refresh.
- [X] T008 [P] Write transport tests in `tests/unit/test_ai.py` and fixtures in `tests/recordings/inference/` for authorized public Responses requests with `store=false` and `stream=true`, supported/default/unavailable models, catalog discovery, completion-gated SSE, fragmented events, refusal, failed/incomplete/interrupted streams, malformed JSON, HTTP/permission/usage-limit failures, deadline and connection timeout, and absence of automatic inference retries or API-key fallback.
- [X] T009 Adapt generic authentication from the research-recorded fyntok revision into `src/job_scan/auth.py`, satisfying T007: separate job-scan registration/host identity, returning client ID reuse, browser loopback login with a 15-minute deadline, identity and plan-scope validation, protected per-registration records with refresh/selection, and local cleanup plus attempted revocation retaining registration identity. Use `$XDG_CONFIG_HOME/job-scan/` or `~/.config/job-scan/` with owner-only permissions; inspect source only, never sibling credentials. Preserve attribution in `specs/001-assess-job-posting/research.md`.
- [X] T010 Implement the subscription adapter and typed safe failures in `src/job_scan/ai.py`, satisfying T008: authorized catalog and Responses calls, default `gpt-6.1-sol` with low reasoning and explicit model override, strict schema request and complete-response decoding, 180-second total inference deadline and 10-second connection timeout, completion required before success, no automatic inference retry or model substitution, and no API-key billing path. Depend on T006 and T009; preserve generic source attribution.

**Checkpoint**: Offline tests establish strict contracts and the provider lifecycle. Live account eligibility remains unverified.

## Phase 3: US1 — Understand work arrangements from posting HTML (P1, MVP)

**Goal**: Read one saved posting, assess its work arrangement using intact HTML, validate evidence, apply preferences, and print a readable report with explicit uncertainty.

**Independent test**: Invoke the real `main(argv)` against curated HTML and HTTP-boundary recordings with real auth, prompt, SSE, schema/evidence validation, preferences, and rendering. Verify FR-001–FR-007 and all six acceptance scenarios; then separately evaluate semantic quality live against reviewed expectations for SC-001–SC-004.

### Examples and review

- [X] T011 [US1] Create a coverage/review matrix in `evaluations/coverage.md` mapping FR-001–FR-007, SC-001–SC-004, all six scenarios, and edge cases to `evaluations/cases/posting-01/` through `posting-03/` and focused fixtures; preserve approved `expected.json` values and posting hashes, record pending source-content reviews accurately, and distinguish absent annotations from explicit checked absences. Roughly ten shared cases is optional, not a release gate.
- [X] T012 [US1] Author focused HTML, provenance, and manual expectations under `evaluations/fixtures/` for explicit hybrid allowance and expectation (quantities/ranges, periods, conditions), qualitative schedules, remote arrangement alongside excluded eligibility/time-zone text, missing arrangements, conflicting evidence, office days without a stated workweek, flexible/occasional home working, ambiguous target roles, loading-only and unusable input, and page instructions treated as untrusted source content. Keep rich reusable postings intact and do not derive expectations from model outputs; update `evaluations/coverage.md`.
- [X] T013 [US1] Add the SC-002 paired fixtures and expectations under `evaluations/fixtures/structure-pair/`: keep the same words while changing role/location HTML associations and require different expected findings; cover headings, lists, and table associations in `evaluations/coverage.md` and retain evidence context beyond isolated schedule words.
- [X] T014 [US1] Prepare owner review of source content in `evaluations/cases/posting-01/metadata.json`, `evaluations/cases/posting-02/metadata.json`, `evaluations/cases/posting-03/metadata.json` and new `evaluations/fixtures/` content/expectations; record actual review outcomes and exact hashes in `evaluations/coverage.md`. Existing criterion approvals stand while hashes match; do not automatically approve content or new expectations. Pending review blocks acceptance/live golden success, not independent coding tasks.

### Tests first

- [X] T015 [P] [US1] Write evidence tests in `tests/unit/test_evidence.py` for exact substrings, repeated and overlapping occurrences, invalid indexes/quotes, Unicode offsets, multiline/minified HTML, computed half-open spans and line locations, and context-sensitive evidence; quote matching alone must not assert semantic relevance.
- [X] T016 [P] [US1] Write criterion and report tests in `tests/unit/test_work_arrangement.py` and `tests/unit/test_report.py`: intact HTML/schema prompt, untrusted page content, remote preferred/hybrid acceptable/on-site outside preferences, retained work-arrangement conditions/alternatives/conflicts and exclusion of candidate geography, right-to-work and time-zone details, no eligibility inference or hard rejection, qualitative/missing schedules and no arithmetic from office days; assert report sections/source identity/excerpts/locations rather than exact prose.
- [X] T017 [P] [US1] Write input and CLI contract tests in `tests/unit/test_cli.py`: readable regular file, nonempty UTF-8 with optional BOM, exact decoded HTML/original-byte hash, 262,144-byte boundary, oversize/invalid/unreadable/missing inputs before inference, one-file arguments, HTTP(S)-only provenance without fetching, model override, stdout/stderr separation, and exits 0/1/2/130 per `specs/001-assess-job-posting/contracts/cli.md`.
- [X] T018 [P] [US1] Write system workflows in `tests/system/test_cli.py` with sanitized actual-provider recordings for successful inference and clearly labelled synthetic OAuth/inference-failure fixtures in `tests/recordings/`: successful remote/hybrid/on-site, uncertainty/conflicts, unusable/ambiguous postings, auth/permission/usage failures, refused/interrupted/incomplete output, invalid schema/evidence, and user interruption; call real `main(argv)` and all internals through the test-only HTTP boundary. Assert no provisional or fabricated success reports and no unexpected network; include auth commands/catalog and separate subprocess installed `--help` smoke coverage in `tests/system/test_entrypoint.py`.

### Implementation

- [X] T019 [US1] Implement pure evidence resolution in `src/job_scan/evidence.py`, satisfying T015: `start`, `end`: “half-open Unicode character offsets computed locally from the selected occurrence”; line numbers derived locally; overlapping occurrence counting, exact excerpts, and rejection of unmatched/out-of-range evidence; retain source context for report rendering.
- [X] T020 [US1] Implement work-arrangement prompts and deterministic fit mapping in `src/job_scan/criteria/work_arrangement.py`, satisfying T016 and the model contract: transmit intact HTML with schema, isolate page instructions as evidence, preserve quantity wording/work-arrangement conditions and role associations, cite positive claims, and distinguish missing data from conflicts; no inferred home-day arithmetic, eligibility or overall apply/reject recommendation.
- [X] T021 [US1] Implement pure readable rendering in `src/job_scan/report.py`, satisfying T016: source path and optional URL, arrangement/work-arrangement conditions, applicable home-working schedule, exact quotes and local source locations, preference-linked fit judgments, uncertainty/conflicts, and retained alternatives; no numeric score or manufactured overall verdict.
- [X] T022 [US1] Implement file loading and the assessment command in `src/job_scan/cli.py`, satisfying T017/T018: “a readable regular file, nonempty UTF-8 (optional BOM accepted), and at most 262,144 bytes”; “Do not normalize whitespace, strip markup, or silently truncate”; hash original bytes and pass intact decoded HTML through provider/schema/evidence/preferences/report stages. Fail for absent/ambiguous posting, succeed with uncertainty for missing criterion details, buffer until fully validated, and implement safe diagnostics and documented exit codes.
- [X] T023 [US1] Wire auth login/status/use/logout and models commands in `src/job_scan/cli.py` to the real auth/transport components; satisfy `specs/001-assess-job-posting/contracts/cli.md` and T018, including returning registrations, secret-free status with no token refresh, foreground login, unavailable model failures, and explicit unconfirmed remote revocation.

### Golden evaluation

- [X] T024 [US1] Write evaluation tests in `tests/unit/test_evaluations.py` for `evaluations/run.py`: selected criterion keys, missing annotations as not evaluated, omitted fields as unchecked versus explicit null/not_stated checks, pending/stale content and criterion rejection, evidence occurrence/relevance separation, semantic findings/prohibited conclusions, mandatory fixture coverage, and unsuccessful outcomes when checks or manual review are incomplete; test the projection rules in `specs/001-assess-job-posting/data-model.md` for scalar versus multiple arrangements, missing versus qualitative schedules, same-finding quantity/period checks, explicit null, and unsupported expectation shapes; use synthetic results, never a live judge model.
- [X] T025 [US1] Implement `evaluations/run.py` and evaluation manifest in `evaluations/coverage.md`, satisfying T024: evaluate selected supported annotations across shared cases and focused fixtures with the real adapter; require explicit `--live`, use manually authored expectations, record missing/pending/stale cases without counting passes, project validated findings into unchanged expectation fields using `specs/001-assess-job-posting/data-model.md` (exact arrangement sets, same-context schedule checks, checked nulls and absent schedules), reject unsupported expectation shapes, verify structured fields/evidence automatically, and record owner review of semantic findings/prohibited conclusions/evidence relevance and SC-004 report usability without exact-prose matching or rewriting expectations. Pending manual checks keep the run unsuccessful.
- [X] T026 [US1] Add developer report serialization/manual-review input to `evaluations/run.py` and document its format in `evaluations/README.md`: record timestamp, Git revision, selected case/criterion keys, input/expectation/prompt/schema hashes, requested and returned model identity when available, reasoning/configuration, per-case outcomes, manual relevance/usability review, and limitations; store reports under `.local/evaluations/`, exclude secrets, and invalidate review when relevant artifacts/model configuration change.
- [X] T027 [US1] Exercise explicit live browser sign-in and account model discovery using the implemented CLI; record account eligibility, actual model/settings and sanitized recording provenance in `specs/001-assess-job-posting/validation.md`, and populate sanitized HTTP fixtures in `tests/recordings/` as needed. Never capture real tokens/callbacks/account details; unavailable provider access remains an explicit unresolved validation dependency.
- [X] T028 [US1] After T014 and T025–T027, run `evaluations/run.py --live --output .local/evaluations/latest.json`, obtain and record owner evidence/semantic/report-usability review, and document SC-001–SC-004 results and limitations in `specs/001-assess-job-posting/validation.md`; all mandatory expectations and the structure-sensitive pair must pass, with approved matching hashes and no pending reviews, before claiming story acceptance. Diagnose failures in implementation rather than automatically changing the oracle.

**Checkpoint**: One usable assessment workflow; code correctness and live semantic acceptance are reported separately. All six scenarios and SC-001–SC-004 must be verified for completion.

## Phase 4: Polish and cross-cutting verification

- [X] T029 [P] Update installation, auth, assessment examples, limits, failure behavior, offline checks, opt-in live evaluation/manual review, and remaining limitations in `README.md` and `specs/001-assess-job-posting/quickstart.md`; keep product scope terminal-only and saved-HTML-only.
- [X] T030 Run the locked install, Ruff lint/format, strict ty checks on src/tests/evaluations, socket-blocked strict-marker pytest with branch coverage and 90% combined threshold, and installed CLI help from `specs/001-assess-job-posting/quickstart.md`; fix substantive failures and record command results and justified narrow suppressions in `specs/001-assess-job-posting/validation.md` without weakening gates or adding implementation-mirroring tests.
- [X] T031 Review completion against FR-001–FR-007, SC-001–SC-004 and each constitution principle in `specs/001-assess-job-posting/validation.md`; confirm auth/transport included in coverage, no secrets in recordings/reports, intact HTML and evidence behavior, criterion separation, and real-component system tests. Keep failed or pending live/manual checks explicitly incomplete.
- [X] T032 Update completed task state and resume notes in `specs/001-assess-job-posting/tasks.md` and `SPEC_KIT_GUIDE.md` with actual verification and unresolved dependencies; the next workflow stage is `$speckit-converge`, followed by implementation of any appended gaps until convergence. Do not claim convergence before running that skill.

## Dependencies and execution order

```text
Setup T001–T004
  → Foundation T005–T010
    → US1 examples/review T011–T014
    → US1 tests T015–T018 → core T019–T021 → CLI T022–T023
    → evaluation tests T024 → runner T025–T026
    → live access T027 → reviewed golden run T028
      → final checks/documentation T029–T032 → converge
```

- US1 is the only story and has no other story dependencies. Foundation blocks story implementation; within the story, review preparation may proceed while code work continues.
- T006 follows T005; T009 follows T007; T010 follows T008, T006, T009. Auth and transport test drafting T007/T008 can overlap after setup.
- T012/T013 follow T011 and share the coverage matrix, so perform them sequentially. T014 follows fixture authoring; pending owner review does not block tests or core development, but blocks T028 acceptance.
- T015–T018 are independent test files after foundation and fixture drafts. Tests must fail meaningfully before their implementation. T019–T021 depend on T006 and their respective tests; T022 depends on all three and T010; T023 follows T022 because both edit cli.py.
- T024 can proceed after fixture drafts; T025 follows T024 and the real assessment pipeline; T026 follows T025 because both edit the runner. T027 follows working auth/CLI and prepares any real-stream compatibility recordings; T028 requires approved fixtures, working runner, and live access.
- T029 can overlap T028 once commands are settled. T030 follows code/documentation changes and recording finalization; T031 follows all verification including T028; T032 follows final review. Repeat affected checks if fixes change relevant behavior.

## Parallel examples: US1

After foundation and fixture drafting, independent test tasks T015, T016, T017, and T018 can proceed together in their distinct files. After those tests establish expected behavior, T019 (`evidence.py`), T020 (`criteria/work_arrangement.py`), and T021 (`report.py`) can proceed independently against the established models. Integrate through cli.py sequentially. These are scheduling opportunities, not instructions to delegate automatically.

## Implementation strategy

The MVP is the single US1 workflow with authentic subscription transport, evidence validation, deterministic preferences, readable output, and failure handling. Deliver it incrementally: establish offline infrastructure and provider boundary, implement the pure core against reviewed examples, integrate the CLI, then validate live semantic quality. Preserve current approved expectations and record owner review only when actually received. Missing source-content approval, new fixture approval, live access, or manual evaluation remain explicit acceptance dependencies rather than reasons to skip useful independent work.

Owner review, consistency analysis and implementation are complete. All 33 tasks are checked,
including the convergence documentation fix below; the final convergence pass found zero
remaining gaps. Next: use/review the saved-HTML CLI or specify a new feature.

Owner refinement on 2026-11-06: T016/T020/T021 and affected golden cases must keep candidate residence, right-to-work/visa and time-zone details out of work-arrangement findings, fit and uncertainty. Revalidate affected behavior with prompt v4; do not alter source HTML.

## Phase 5: Convergence

- [X] T033 Update the stale unimplemented-command status in `specs/001-assess-job-posting/contracts/cli.md` and planned-code labels in `specs/001-assess-job-posting/plan.md` to match the delivered CLI per plan: interface and project structure, T029 (partial; LOW).

## Phase 6: CLI maintenance — 2026-11-09

Owner-authorized technical revision: use Typer for less manual code and clearer command/option
definitions. T034 supersedes T001’s argparse detail; original completion history is retained.

- [X] T034 Replace argparse parser/dispatch with typed Typer command functions and an auth group in `src/job_scan/cli.py`; lock the dependency in `pyproject.toml` and `uv.lock`, per plan: CLI maintenance decision.
- [X] T035 Verify command/option help, malformed arguments, validation before auth, stdout/stderr, exit codes and interruption; run existing CLI/system tests and all required offline checks, per plan: CLI maintenance decision.
- [X] T036 Update technical decision, CLI contract, validation and resume notes with migration scope and actual results; review convergence against the updated artifacts, per plan: CLI maintenance decision.
