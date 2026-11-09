# Quickstart Validation: Personalized Job Ratings

**Status**: Complete and owner-accepted. Implementation, full live/replay validation, bound owner semantic review and final convergence all pass. Earlier checkpoint sections below are historical.

## Prerequisites and setup

Use the repository's Python 3.14 environment on Linux/macOS, uv, and its committed lockfile. Run from the repository root. A live model run additionally requires the existing authorized ChatGPT registration with plan allowance; offline validation does not.

```bash
uv sync --locked
uv run --locked job-scan assess --help
```

Help must show `--profile` and preserve existing options. Copy the shipped starter to an ignored local path and enter your own preferences:

```bash
mkdir -p .local
cp examples/preferences.toml .local/preferences.toml
```

The starter has all weights 1 and empty prose. Enter text for the dimensions you want assessed and choose relative weights 1–5; retain explicit weights for all four. Follow [profile.md](contracts/profile.md). The completed fictional [example](contracts/profile.example.toml) shows two optional exceptions. Relevant configured preference content will be sent to the model. Do not use a personal profile in versioned fixtures or recordings.

## Existing and personalized flows

```bash
uv run --locked job-scan auth login
uv run --locked job-scan assess evaluations/cases/posting-01/posting.html
uv run --locked job-scan assess evaluations/cases/posting-01/posting.html --profile .local/preferences.toml
```

The first assessment preserves the existing work-arrangement report. The second identifies the existing qualitative dimension plus four new dimension outcomes, relevant preferences/evidence, importance, complete/partial overall score with coverage and missing dimensions, or no numeric score when none is rated, and a separate decisive outcome. This posting may not establish company facts needed by your profile; an insufficient-evidence outcome is expected rather than fabricated information. Profile identity appears in the report, and the file is unchanged.

## Targeted validation scenarios

After implementation, the manually authored personalized corpus supplies the fixtures below; their pair IDs and expectation paths must be listed alongside the existing work-arrangement cases in `evaluations/manifest.json`. Filenames for golden postings are detailed in that manifest rather than duplicated here.

| Scenario | How to exercise | Expected result |
| --- | --- | --- |
| Profile sensitivity | Same posting with each dimension's contrasting profiles | Facts/evidence remain consistent; explained fit follows each profile |
| Weights | Fixed-result unit cases with equal and technology/field-heavy weights | Auditable mean with one-decimal final rounding; metadata-only changes do not alter fit request |
| Compelling attraction | Low-scoring posting with confirmed exceptional field interest | Separate worth-pursuing outcome; no numeric bonus |
| Deal-breaker | High-scoring posting with confirmed unacceptable technology | Separate deal-breaker outcome; no numeric penalty |
| Both exceptional types | Confirmed field attraction and technology deal-breaker | “Conflicting exceptions,” evidence for both, no automatic winner |
| Unknown evidence | Posting lacking relevant company facts or exception evidence | Explicit insufficient/unresolved states; no substituted scores; partial overall over rated dimensions with missing dimensions and dimension-count/importance coverage; no overall score if none is rated |
| Empty preferences | Absent, empty, or whitespace-only preferences, with no exceptions | Not configured; omitted from fit requests and weighting regardless of importance |
| Optional exceptions | Omit declarations or use an empty array; then add a valid excerpt-based declaration | No exception request when none are supplied; every supplied valid declaration is evaluated |
| Invalid input | Missing file, malformed TOML, all-blank preferences or importance 0, invalid excerpt reference | Exit 2, actionable stderr, no auth/network or success report |
| Later-stage failure | Recorded exception request timeout/incomplete response | Exit 1 with no partial stdout report |

Use the completed example as an input-format smoke check after implementation:

```bash
uv run --locked job-scan assess evaluations/cases/posting-01/posting.html --profile specs/002-personalized-job-ratings/contracts/profile.example.toml
```

Do not expect both example exceptions to match arbitrary legacy corpus HTML. Only the corresponding authored golden posting establishes that semantic case.

## Required offline checks

```bash
uv run --locked ruff check src tests evaluations
uv run --locked ruff format --check src tests evaluations
uv run --locked ty check src tests evaluations
uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90
uv run --locked python evaluations/run.py --check --output .local/evaluations/readiness.json
```

Lint, formatting, type checking, and tests must pass. Inspect the `--check` report for readiness: all mandatory readiness checks must pass, but exit 1 remains expected until an accepted review exists. Readiness does not establish live acceptance.

Successful system paths replay sanitized actual-provider responses; no unrecorded sockets are allowed. New corpus source/expectation reviews must be genuinely complete for readiness; pending statuses must not be silently bypassed.

## Live evaluation and acceptance

Run only when intentionally validating model semantics with available subscription allowance:

```bash
uv run --locked python evaluations/run.py --live --recordings-dir tests/recordings/inference --output .local/evaluations/latest.json
```

Inspect reports against manually authored sources/preferences/expectations. The runner automatically loads the one manifest and evaluates the full suite. Author one owner review using the exact run ID and all case IDs from its report: preserved posting-path IDs for work arrangement and pair IDs for personalized entries. Review the separate numeric/exception behavior and source attribution; exact model wording/scores need not repeat. Record the model/configuration and limitations. See [evaluation contract](contracts/evaluation.md) and the existing `evaluations/README.md` for review fields and recording hygiene.

```bash
uv run --locked python evaluations/run.py --review .local/evaluations/latest.json --manual-review .local/evaluations/manual-review.json --output .local/evaluations/reviewed.json
```

Acceptance requires all mandatory automatic and owner semantic checks to pass on current hashes, required offline checks to pass, and convergence to find no remaining required work. A cassette replay, readiness pass, or this plan alone does not establish feature acceptance.

## Implementation baseline (2026-11-09)

`uv sync --locked` passed without dependency changes (Python 3.14.4). Ruff lint/format and strict ty passed. The socket-blocked baseline suite passed 96 tests with 97.30% combined statement/branch coverage. Existing strict settings and exact pins are retained.


## Implementation checkpoint (2026-11-09)

Core profile parsing, strict responses, independent criterion prompts, evidence assembly,
Decimal weighting, exception matching/reduction, bounded CLI loading, atomic reporting,
starter guidance, unified evaluation and review binding are implemented. The manifest has
47 cases: 16 preserved baseline cases and 31 fictional personalized pairs. Their owner review
index is [evaluations/personalized/README.md](../../evaluations/personalized/README.md).

Actual verification at this checkpoint:

- `uv sync --locked`: passed; Python 3.14.4 and all exact dependency pins/lockfile retained.
- Ruff lint, Ruff formatting and strict ty: passed across `src tests evaluations`.
- Full socket-blocked pytest command: **264 passed, 32 failed**; **97.85% combined
  statement/branch coverage**, above the 90% target. Every failure explicitly reports a missing
  actual-provider cassette in `tests/system/test_personalized_cli.py` (31 required pairs plus
  the successive-profile test). No synthetic successful recording or silent skip was substituted.
  Local log: `.local/evaluations/offline-checks.log`.
- All 16 existing actual-provider replay cases still pass; original request-byte regression
  checks pass. Synthetic stage-failure tests exercise HTTP/schema/evidence/refusal/incomplete/
  timeout/registration/interruption failures without partial stdout, using real internal components.
- Installed `uv run --locked job-scan assess --help` exposes `--profile`, `--source-url`, `--model`.
  Profile unit checks verify BOM/original-byte hashes, 64-KiB bounds, one read, immutability and
  validation before auth/network construction. The starter remains intentionally incomplete.
- Offline readiness: exit 1 / `accepted=false`, **16 ready**, **31 pending_review**, no mandatory
  coverage issues or stale hashes. Current report: `.local/evaluations/readiness.json`.
  All new source and expectation markers remain `pending_owner_review`.

48 tasks are checked. T027/T038/T042/T050 have recorded-success dependencies still outstanding;
T042's failure matrix passes, while successful unknown-state CLI validation awaits actual cassettes.
T053 requires genuine owner source/expectation review; T054 then captures the full mixed-mode live
suite. T055–T058 require those recordings, fresh full checks, bound actual owner semantic review,
remaining quickstart live/usability scenarios and convergence. No live inference, owner approval,
or feature acceptance is claimed.

Constitution review at this checkpoint: CLI/simple fixed criteria, evidence/uncertainty, separate
criterion policy, locked exact pins and strict tooling are preserved. The remaining open gates
are actual personalized replay and owner-reviewed golden semantic acceptance, followed by
convergence. Coverage alone does not close those gates.


## Owner source approval

The owner replied “looks good” to the 31-pair source/expectation review request. This approval
is recorded in all 31 personalized source metadata and expectation review markers, without
changing source HTML, profile bytes or expected assertions. This approves the inputs only;
review of a current immutable live run remains a separate T056 gate. Pending-review unit
tests now use copied temporary fixtures, so they remain valid after real corpus approval.


## Live capture attempt after source approval

All 216 unit tests pass after isolating pending-review fixtures; Ruff lint/format and strict ty
pass. Offline readiness now reports all 47 cases `ready`, no coverage issues and exit 1
(`accepted=false`, as required until a bound semantic review exists). T053 is complete.

The full authorized T054 command was attempted with the existing selected model and actual
transport. The saved registration had inference permission, but its expired refresh credentials
were rejected; the authentication lifecycle cleared unusable credentials and requires sign-in.
All 47 cases therefore failed at the work-arrangement stage before inference. No new provider
cassettes were captured. The failed attempt is retained in `.local/evaluations/latest.json`
and `.local/evaluations/live-run.log`; it is not an acceptance candidate.

An encrypted one-time transfer recipient has been prepared with the existing
`evaluations/auth_transfer.py` helper. The owner must sign in again, then export from their
signed-in terminal; the worker can import the encrypted envelope and rerun the complete
T054 suite. No credential values are placed in chat or versioned artifacts. T054–T058 and
recording-dependent T027/T038/T042/T050 remain incomplete.


## Restored authentication and live-discovered corrections

The encrypted export arrived and was imported successfully; the transfer envelope/private
key were removed by the existing helper. The earlier authentication-only failure is archived
as `.local/evaluations/auth-failure.json`. The first authenticated run completed all inference
stages with 44 automatic passes and three failures, archived in
`.local/evaluations/before-evidence-and-exception-fixes.json`.

Two technology cases used valid smaller citations from the expected source passage. The
evaluator now compares resolved raw-HTML passage locations rather than requiring one exact
long quotation; a regression test rejects a citation at a different occurrence. Owner review
still establishes relevance and entailment. The same-dimension opposing-declaration case
exposed a prompt ambiguity: exception prompt v2 treats declaration kinds as authoritative
metadata and requires both matches when their shared condition is evidenced. Approved golden
inputs and assertions are unchanged. A contract preflight also corrected source metadata
identity: one reviewed posting can be reused by distinct profile-pair IDs, while expectations
still bind strictly to each pair. A failing-then-passing regression covers that reuse.

The superseded refresh was stopped before changing bound code, preserving captured streams
in place. Ruff lint/format and strict ty pass; 244 unit and synthetic failure-path tests pass.
A new complete live run is in progress against the final code. No earlier run is accepted.

The documented starter workflow was also exercised with a fictional edited copy and actual
provider replay: an empty starter exits 2 with zero requests, legacy assessment exits 0 with
one request, and personalized assessment exits 0 with two. The edited profile hash is
unchanged after assessment, blank dimensions are not configured, and a provenance URL adds
no network request. `.local/evaluations/quickstart-smoke.json` records these checks.


## Current accepted validation

- Immutable run: `b1d1383f7a6856baf98353aa9b9133bc0455ead4951eb5bf26d732eb31aa0486`.
- Configuration: requested and returned `gpt-6.1-sol`; low reasoning on every stage.
- Automatic checks: **47/47 passed**, across all 16 baseline and 31 personalized cases;
  89 completed stages and 64 distinct current request hashes/cassettes.
- Offline checks: Ruff lint, Ruff formatting and strict ty passed; **298 tests passed**,
  sockets blocked, **98.04% combined statement/branch coverage** (target 90%).
- Actual source/expectation approval and explicit owner approval of all 47 actual results
  have been received. The full-suite review command exited 0 with **accepted=true**.
- Acceptance artifacts: `.local/evaluations/latest.json`, `manual-review.json`, `reviewed.json`,
  and the readable `.local/evaluations/review.md`. Earlier failed/interrupted candidates
  remain historical and do not supply this approval.
- All current recordings passed hygiene checks; no credential values were found. Eleven
  unused development cassettes were archived under ignored `.local/evaluations/`.
- Final starter smoke replay passed with a fictional edited starter (not personal preference
  content), unchanged profile hashes, no network for an empty starter, one request for
  legacy mode and two for personalized mode. `quickstart-smoke.json` records these checks.

Limitations: subjective model scores and wording can vary between byte-identical requests.
Quote existence/passages establish provenance; the owner's bound review establishes semantic
relevance, sufficient evidence, required/prohibited findings and report usability for this
corpus and configuration. New code, prompts, schemas, inputs, model configuration or lockfile
changes require fresh bound validation; documentation-only progress notes do not.


## Final convergence and constitution review

**Complete: 58/58 tasks.** Convergence checked 15 FRs, 8 SCs, 21 user-story acceptance
scenarios, 14 plan obligations and all 6 constitutional principles. There are zero findings
by gap type or severity, no remaining required work and no remediation tasks to append.
The read-only convergence pass left tasks.md byte-for-byte unchanged; implement then marked
T058 complete.

Constitution I–VI pass: simple fixed CLI architecture, explicit source evidence/uncertainty
with actual owner semantic review, independent criterion policies, exact locked dependencies
and strict verified tooling, preserved CLI behavior, and manually authored golden inputs with
current bound live/replay acceptance. No constitutional violation or amendment remains.

Accepted run `b1d1383f7a6856baf98353aa9b9133bc0455ead4951eb5bf26d732eb31aa0486` is still bound to the current
application/evaluation/configuration/input hashes. `reviewed.json` has `accepted=true`, all
47 cases pass automatically and have actual owner approval, and all 298 offline tests pass
at 98.04% combined coverage. Only documentation/progress records changed after acceptance;
no extra inference was needed. The implementation is ready for repository review.
