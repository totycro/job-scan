# Implementation validation

Status: complete and converged on 2026-11-06. Implementation, offline checks, all 16 live cases and owner report review pass.
Feature: `001-assess-job-posting`. Scope refinement: the owner excluded candidate residence,
right-to-work/visa eligibility and time-zone requirements from this work-arrangement criterion.
The saved HTML remains intact; relevant office attendance and home-working schedules remain.

## CLI maintenance validation — 2026-11-09

The owner authorized a Typer migration for clearer command/option definitions and less
manual parser/dispatch wiring. Typer 0.28.0 is locked; commands are typed functions with an
auth group. Input loading still precedes session creation. Reports and the assessment
pipeline are unchanged. Help uses Typer; safe argument diagnostics remain on stderr.

The required locked install, Ruff lint/format, strict ty and installed CLI help all pass.
The full socket-blocked suite passes **96 tests, no skips, 97.30% combined coverage**.
Sixteen new regression cases cover malformed arguments, command/group/option help without
opening auth resources, redirected help without ANSI escapes, and command interruption.
The interruption test caught Typer returning 130 in non-standalone mode; the wrapper now
propagates it with the existing diagnostic. Terminal help was inspected as well.

Final convergence on 2026-11-09 found zero remaining findings across 11 requirements/success
criteria, six acceptance scenarios, 15 plan decisions, six constitution principles and all
36 tasks. No extension hooks are configured; no convergence tasks were appended.

No fresh live evaluation was run: prompts, response schema, golden inputs/expectations,
provider implementation and report rendering did not change. The accepted 2026-11-06 live
run below remains evidence for assessment quality, not a live run of this CLI revision.

## Deterministic checks (original increment)

Final offline run after the scope refinement: **80 tests passed, no skips, 97.33%
combined statement-and-branch coverage**. Authentication and transport are included; transport,
evidence, models and reporting achieved 100% in that run. The final run uses the current prompt's actual recordings.

The following checks passed with the locked dependencies:

- `uv sync --locked`
- `uv run --locked ruff check src tests evaluations`
- `uv run --locked ruff format --check src tests evaluations`
- `uv run --locked ty check src tests evaluations`
- `uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90 -q`
- `uv run --locked job-scan --help`

Tests block unrecorded sockets. Actual-provider inference is replayed through HTTPX with
method/URL/request-body hash matching. Missing actual-provider recordings now fail with the
case name and expected path instead of skipping. A fresh offline verification on 2026-11-06
after this test-only change passed all 80 tests with no skips and 97.33% combined coverage,
plus Ruff lint/format, strict ty and installed CLI help. No new live evaluation was needed
because assessment behavior did not change.

OAuth uses synthetic identities, locally generated RSA
signatures and synthetic discovery/token responses; no real OAuth traffic or credentials are
recorded. Failure cassettes are labelled synthetic. The subprocess smoke test uses installed
`job-scan --help`; ordinary system workflows use real `main(argv)` and internal components.

Narrow lint exemptions cover fake test credentials, fixed local subprocess commands, the
OAuth token endpoint string, and intentionally suppressed callback logging. All other
selected lint/type rules remain enabled; there are no global Any or unresolved-import escapes.

## Live validation

The user completed browser sign-in in their VM. The worker initially had no registration.
An authorized encrypted handoff transferred only the active job-scan registration through the
shared, Git-ignored workspace. The worker retained its own stable host ID; private credentials
and the ephemeral private key stayed outside the workspace. Import removed transfer artifacts.
The worker successfully discovered the account catalog; `gpt-6.1-sol` is available.

Configuration: `gpt-6.1-sol`, reasoning `low`, strict JSON schema, intact HTML, public Responses,
`store=false`, `stream=true`, 180-second total inference deadline, no automatic inference retry
or API-key billing fallback. Requested and returned model identity is recorded per case.

Three shared cases and thirteen focused cases have owner-approved content/expectations with
matching HTML hashes. Initial prompt v1 passed 14/16 automatic checks; v2 passed 15/16. Those
runs exposed tentative home-working availability interpreted as a policy, and period text
repeated across quantity/frequency fields. Prompt/schema refinements addressed these cases.
Prompt v3 passed all 16 automatic checks. The owner then rejected the excessive attention to
candidate geography and time zones in posting-02. The owner narrowed the criterion's scope;
related specification, expectations and prompt v4 reflect that instruction. Approved source
HTML was not changed to obtain a pass.

Prompt v4 passed all 16 automatic checks. The owner reviewed and approved the updated reports on 2026-11-06; bound manual-review application returned exit 0 with `accepted=true`. Reports are under `.local/evaluations/`; these record
Git/source/input/expectation/metadata/prompt/schema hashes, model/configuration, findings,
evidence, outcomes and limitations. Current sanitized SSE cassettes are in `tests/recordings/`.
Earlier prompt revisions and recordings are archived under ignored `.local/evaluations/`.

**Owner semantic/evidence/usability review is accepted for the exact run below.** Automatic field/quote checks
and replay do not establish semantic correctness. The reviewed reports are in
`.local/evaluations/review.md`; bound manual reviews are applied using `evaluations/run.py`.
No human approval of reports is inferred from dataset approval or passing automatic checks.

## Requirements and constitution review

| Obligation | Implementation / verification |
| --- | --- |
| FR-001: one HTML input, provenance, failures | cli.py loader and argument checks; test_cli.py; installed help |
| FR-002: meaningful structure | intact HTML request; structure-pair cases and actual replay |
| FR-003: arrangement separate from fit | criterion module and deterministic fit mapping; remote/hybrid/on-site cases; eligibility excluded by owner refinement |
| FR-004: hybrid schedules | strict model/prompt; allowance, expectation, qualitative, office-days and missing cases |
| FR-005: evidence and identity | exact quote/occurrence checks, local Unicode spans/lines, source path/URL; owner evidence relevance review passed |
| FR-006: uncertainty and failure | strict completion gating; missing/conflict/ambiguous/loading cases; synthetic failure system tests |
| FR-007: report | pure renderer with facts, schedules, fit, source excerpts and uncertainty |
| SC-001–SC-004 | all 16 mandatory cases passed; owner relevance/semantic/usability review approved |
| I: simplicity | one synchronous CLI; no database or criterion framework |
| II: evidence/uncertainty | local provenance checks; manual entailment gate; no fabricated absence evidence |
| III: separate criteria | work-arrangement instructions/preferences isolated in criteria/work_arrangement.py |
| IV: development | strict checks and 90% combined coverage gate; pure core/imperative shell; HTTP-boundary system tests |
| V: CLI | assess, auth and models commands |
| VI: validation | owner-reviewed sources/expectations; recorded and live checks kept separate |

No constitutional amendment is required. Report acceptance is recorded. The first convergence pass appended T033 for stale documentation status; it was completed. The final pass reported zero findings across 11 requirements/success criteria, six acceptance scenarios, 14 plan decisions, six constitution principles and all 33 tasks. No extension hooks are configured.

## Limits

Only 16 curated cases are covered. Passing them does not prove reliability on arbitrary pages
or future model changes. The default low-reasoning model required prompt iteration. No browser
rendering or URL fetching exists. Full original posting-03 (2,144,770 bytes) exceeds the approved
256 KiB input limit; its unchanged generic fixture is 62,393 bytes. No production preprocessing
is implemented. Account eligibility/usage limits remain account-specific. No real remote OAuth
revocation was exercised during validation; synthetic tests verify cleanup and reporting.

## Accepted evaluation record

- Timestamp: `2026-11-06T07:05:27.439303+00:00`
- Git revision: `0a10fb7c89c8ecbfb300ecab16966a01cbbde713` (implementation changes were uncommitted; the source hash below binds their actual bytes).
- Source/lockfile/manifest hash: `40d5ee0411c91c50753709dc1f9ec8008ddc6ec5210fd1a66ff2657abd3d44b9`
- Run ID: `cf3df394d575225d25df9f147bfcfe2931ca547485e06dd12096181807e066c8`
- Prompt: `work-arrangement-v4`; SHA-256 `5385277ed37abea22b47ddcdfb25369906dc64a276451c1a3dfe5ad597ec5c73`
- Response schema SHA-256: `3767e74a0fbba88122e2b50fd5997c0811852309a36845a0e154274f9468349f`
- Requested/returned model: `gpt-6.1-sol`; reasoning `low`.
- Owner review: approved updated reports on 2026-11-06, including relevant evidence and usability.
- Full report: `.local/evaluations/reviewed.json`; manual review: `.local/evaluations/manual-review.json`.

| Case | Automatic | Owner review | Input SHA-256 |
| --- | --- | --- | --- |
| cases/posting-01 | Pass | Approved | `a49831c4537fdc0f1aa4949a5c46f0a981ed15499c31556e51ca049133a39a94` |
| cases/posting-02 | Pass | Approved | `53910077955652647907ebd17f6f516df22cb63f9cea2ca26de6026a552a5651` |
| cases/posting-03 | Pass | Approved | `841c613ba9c9946dfd11dff92a6c140912f44d11bdbd348ea830d5d199cc3fd2` |
| fixtures/ambiguous | Pass | Approved | `54396c84207dce8de72fb32cafe416d50a5b714c06669e3c36a75a6e3d295355` |
| fixtures/conflict | Pass | Approved | `c42c69277fe34ecd709e85fb24bdaade6cd300713eea3e9a727b30ad081b1482` |
| fixtures/flexible | Pass | Approved | `0f9bfd4a2c97cde81015dfe8738869a8f498f26ad2fcc6a1e919fbc545433dda` |
| fixtures/hybrid-allowed | Pass | Approved | `81baab894e25cf6dd80d02e2835adf7389184557bc012e3708aa2688a2e929b2` |
| fixtures/hybrid-expected | Pass | Approved | `4ea2e421d4054dd6e44f97598e23821421795440a3a76ca95b55c509f93c9cbe` |
| fixtures/loading | Pass | Approved | `e9643d2449f41280415d06dd031780f3dbc9d4aa708863105768057218737188` |
| fixtures/missing | Pass | Approved | `54073ccfa3892342743d17af2d195887b0723f3fa3ad2f3a33b4462edac760a7` |
| fixtures/office-days | Pass | Approved | `ea9a01996d2a0cdb98562b68ce2ac11a669bcb051d4b0651b2c8f4b8ab2599bb` |
| fixtures/qualitative | Pass | Approved | `090f88e089eb62d2c3f24b593d67d334a4ef6cd94647f5ed2e7a04bf0eb74909` |
| fixtures/remote-restrictions | Pass | Approved | `3949d39bbf3629a8120c777dc38cfd30d72f0899279de6a85583074458582851` |
| fixtures/structure-pair/allowed | Pass | Approved | `0d90128482619826066f167446e5980539be83b72331e8911e5bff8fc9a37196` |
| fixtures/structure-pair/expected | Pass | Approved | `6bed9984c2cc1887968a89dfc989776b36052a159e51fd90ae889e84e6caba62` |
| fixtures/untrusted-instructions | Pass | Approved | `efe4b26f0779681e2c25e549b41f688cfc363176bdcc32a9ee5e5aa892995cf5` |
