# Implementation Plan: Assess a Job Posting

**Branch**: `main` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)
**Status**: Design draft for owner review. Three generic example drafts and owner notes are available; detailed expectations, remaining coverage, and the input-size limit need review before adoption. No tasks or implementation have been created.

## Summary

Build a Python CLI that reads one HTML file, asks ChatGPT for evidence-backed work-arrangement findings, validates the response, applies the owner's preferences, and prints a report. Pass HTML intact; do not build a webpage-fetching or text-extraction pipeline.

**Agreed technical constraints**: Python unless a clearly better choice emerges; ChatGPT subscription use rather than metered API-key billing; ty for type checking, prioritizing iteration speed. The owner identified `../fyntok/src/fyntok/ai.py` as the integration reference.

**Proposed choices**: Python 3.14, uv, HTTPX, PyJWT, Pydantic, argparse, Ruff, and pytest; adapt the reference's generic transport/authentication locally. These choices await review. Decisions and alternatives are in [research.md](research.md).

## Technical Context

| Item | Design choice |
| --- | --- |
| Language/version | Python 3.14; pin the minor in `.python-version` and project metadata |
| Dependencies | HTTPX for OAuth/streaming; PyJWT with crypto for identity validation; Pydantic 2 for response schema/validation; stdlib argparse for CLI |
| Development | uv and committed lockfile; Ruff; ty with strict settings below; pytest, pytest-cov, pytest-socket |
| Storage | No assessment database. Protected app-local OAuth credentials; versioned golden inputs/expectations and sanitized transport recordings; developer evaluation reports |
| Platform/type | Personal synchronous CLI on Linux/macOS; Windows support deferred because reference auth uses Unix file locking |
| Performance | One assessment/request at a time; 180-second total inference deadline, 10-second connection timeout; no automatic inference retry |
| Limits | One UTF-8 HTML file, up to 256 KiB, no silent truncation. Proposed limit needs review: supplied case 03 is 2,144,770 bytes; smaller curated fixtures do not validate full-page support |
| Model | Start with reference model `gpt-6.1-sol`, reasoning `low`; verify availability for the signed-in account. Optional `--model` selects another available model; no automatic substitution |
| Billing | OAuth permission for ChatGPT plan usage only. No API-key billing fallback; eligibility/limits remain account-specific |

## Constitution Check

Pre-research gate: the approved spec has no known constitutional violations. Research must preserve its narrow scope and define all mandated checks. Post-design review:

| Principle | Design evidence | Result |
| --- | --- | --- |
| I. Keep it simple | One process, one criterion module, raw HTML input, no database or orchestration framework | Pass |
| II. Evidence and uncertainty | Validate source excerpts locally; keep uncertainties/conflicts; semantic evidence review against golden expectations | Pass by design |
| III. Separate criteria | Work-arrangement prompts/interpretation/preferences live in `criteria/work_arrangement.py`; no runtime criterion framework | Pass |
| IV. Development practices | Strict lint/type settings and coverage below; TDD preference; pure validation/formatting with imperative file/auth/network shell; real-component CLI tests | Pass by design |
| V. CLI | Packaged `job-scan` command, readable terminal report | Pass |
| VI. Validation | Manually authored, owner-reviewed HTML/expectations; recorded offline tests plus live semantic evaluation and results report | Pass by design; three generic drafts available, owner review and coverage pending |
| Boundaries/workflow | No fetching, website authentication, company research, commute, scoring, or report-management feature; spec/plan/tasks review preserved | Pass |

No amendment or complexity exception is needed. These are design checks, not claims that software passes validation.

## Design

1. Validate/read the file and retain its exact decoded HTML and SHA-256 of the input bytes. The optional URL is provenance only and is never fetched.
2. Build one work-arrangement request containing the intact HTML and response schema. Treat page content as evidence, never instructions. Do not execute HTML, scripts, tools, or linked resources.
3. Use a local adaptation of the reference's subscription Responses transport and OAuth session. Wait for `response.completed`; reject refusals, incomplete/failed/interrupted streams, malformed JSON, and schema errors. Do not print provisional model output.
4. Resolve each evidence excerpt against the exact HTML, using an occurrence index for repeated excerpts. Generate source spans/line locations locally. Reject missing quotes or invalid occurrences. Citation existence does not prove that the claim follows from it; golden-case evaluation checks that separately.
5. Apply remote-preferred/hybrid-acceptable judgments deterministically to the validated findings. Preserve multiple arrangements and conflicting statements without manufacturing one overall verdict. Render facts, fit, evidence, and uncertainty separately.

Adapt only generic OAuth and stream handling from the reference, with its source revision recorded in research. Use a `job-scan` registration and credential directory; do not import the whole sibling app or read/copy its credentials. Keep account registration, refresh, sign-out, and protected storage behavior. Authentication here is to ChatGPT, not to job sites. See [CLI contract](contracts/cli.md) and [data model](data-model.md).

## Verification

- Prefer TDD for evidence validation, preference mapping, and failures, using owner-reviewed expectations first.
- Ruff: `select = [E,F,W,I,UP,B,SIM,C4,ANN,S,RET,ARG,PTH,RUF]`, Python 3.14 target, 100-character lines, plus format checking. Allow `S101` only in tests; any other narrow suppression must explain the boundary it addresses.
- ty: check `src`, `tests`, and `evaluations`; set `[tool.ty.rules] all = "error"`, `[tool.ty.analysis] strict-generic-narrowing = true` and `strict-equality-semantics = true`, and `[tool.ty.terminal] error-on-warning = true`. Ruff's annotation rules require complete function annotations. Decode unknown JSON into validated models; no global unresolved-import or Any suppression. Pin ty in the lockfile. See [ty configuration](https://docs.astral.sh/ty/reference/configuration/).
- Coverage target: at least **90% combined statement-and-branch coverage** over all application modules, including auth/transport, measured with branch coverage enabled. This is not a separate 90% branch-only threshold.
- Small system suite calls the real `main(argv)` with real file loading, prompt construction, auth session logic, SSE parsing, validation, preferences, and rendering. Replay sanitized recorded HTTP responses through HTTPX's transport boundary; seed a synthetic unexpired session. Match method, URL, and request-body hash; unmatched requests fail. Replay transport and network blocking remain test-only. One subprocess smoke test checks the installed command's `--help`.
- Recorded: inference streams and OAuth/discovery/refresh/revocation HTTP exchanges. Auth failure tests may use deliberately synthetic HTTP fixtures. Never record real tokens, login callbacks, or personal account details. Block all unrecorded network in ordinary tests. No external webpage calls exist.
- Live: explicit browser sign-in, account model discovery, and an opt-in golden evaluation using the actual subscription transport. Do not run live calls in routine tests. Record git/data/prompt/schema revisions, model/settings, timestamp, per-case semantic results, evidence review, and limitations. Expectations remain manually authored; recordings never become the oracle.
- Acceptance requires every spec-defined mandatory expectation to pass, plus owner review of evidence relevance and structure-sensitive associations. Code coverage and cassette replay do not establish LLM quality.

## Project Structure

### Documentation (this feature)

`plan.md` is the review entry point; `research.md` explains choices; `data-model.md` defines validated data; `contracts/cli.md` defines command behavior; `quickstart.md` describes future validation. `tasks.md` belongs to the next stage and is not generated here.

### Source Code (repository root; planned)

```text
pyproject.toml, uv.lock, .python-version
src/job_scan/
  cli.py, auth.py, ai.py, models.py, evidence.py, report.py
  criteria/work_arrangement.py
tests/
  unit/, system/, recordings/, conftest.py
evaluations/
  cases/<case-id>/posting.html, expected.json
  run.py
```

The CLI owns file/auth/network effects. Pure functions validate evidence, map preferences, and render output. Avoid a generic plugin system. Evaluation reports are developer verification artifacts, not saved-assessment product functionality.

## Review and Resume

The design artifacts remain a draft. Three [genericized example drafts](../../evaluations/cases/README.md) now preserve the owner's short notes; their detailed expectations are agent proposals awaiting owner review. Further cases are needed for full spec coverage. The original on-site page exceeds the proposed input-size limit, which must be revisited before plan adoption; reducing fixtures is not a runtime solution to that limit. Review the remaining stack, input limit, auth adaptation, coverage target, and manually authored expectations before finalizing the plan. No subscription request, dependency installation, or application implementation has run. A separate public iframe document was downloaded only to recover the supplied remote example; the product's fetching scope is unchanged.

After plan adoption, the next command is `$speckit-tasks`, followed by review of its task list. Do not advance automatically.
