# Quickstart Validation Guide

**Status**: Implemented commands. Locked installation, Ruff, strict ty, offline tests and installed CLI help have passed. Live semantic results and owner review are recorded in [validation.md](validation.md).

## Prerequisites

Python 3.14, uv, a terminal on Linux/macOS, and a browser on the host for ChatGPT sign-in. Live runs require account eligibility and granted plan permission; they use subscription allowance. Ordinary tests need neither a real account nor network access.

## Install and deterministic checks (after implementation)

From the repository root, using the committed lockfile:

```bash
uv sync --locked
uv run --locked ruff check src tests evaluations
uv run --locked ruff format --check src tests evaluations
uv run --locked ty check src tests evaluations
uv run --locked pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90
uv run --locked job-scan --help
```

Expected: lint, formatting, and strict type checking pass; network-blocked unit/system tests pass with at least 90% combined statement-and-branch coverage. Real CLI internals consume recorded inference streams through the HTTP transport boundary. Test-only OAuth fixtures use synthetic identities/tokens. Unknown requests fail instead of going live.

## Sign in and assess (explicit live operation)

```bash
uv run --locked job-scan auth login
uv run --locked job-scan auth status
uv run --locked job-scan models
uv run --locked job-scan assess evaluations/cases/posting-01/posting.html
```

The `posting-01` rich generic HTML draft now exists; the owner's note labels it hybrid with unspecified days. Detailed expectations were owner-approved on 2026-11-06; source-content review is also approved. Other generic cases cover remote work and an on-site target alongside hybrid related-job cards; see the [case notes](../../evaluations/cases/README.md). Sign-in must finish in the foreground before the assessment runs. Verify that the configured model appears in the account catalog; use `--model` if selecting another supported account model and record that choice.

Expected: remote/hybrid facts and schedule details are distinguishable from fit judgments; quoted HTML and locations support claims; case 01 does not invent a home-working day count. Owner-approved focused fixtures cover allowance-versus-expectation validation. See [CLI contract](contracts/cli.md) for output/exit codes and [data model](data-model.md) for evidence validation.

## Live golden evaluation (separate from code coverage)

All required source content and `criteria.work_arrangement` expectations are approved with matching input hashes. To run a fresh evaluation:

```bash
uv run --locked python evaluations/run.py --live --output .local/evaluations/latest.json
```

The repository ignores `.local/` in Git. This explicit command uses real ChatGPT requests and writes a developer evaluation report, not saved-assessment product functionality. Compare against every mandatory expectation from SC-001–SC-004, including changed HTML associations with unchanged words. The runner selects `work_arrangement` from the shared corpus and checks structured expectations/provenance. Missing criterion keys are not evaluated, and pending/stale reviews cannot count as passing; the owner reviews whether evidence actually supports findings and records the result. It returns unsuccessful if a mandatory check fails or manual review remains pending.

Record model/configuration, prompt/schema and case hashes, Git revision, results, manual evidence review, and limitations. Do not claim semantic validation passed on the strength of fixture replay or coverage. Never generate expected answers by copying model output.

## Failure checks

Try a nonexistent file, empty input, a loading-only HTML snapshot, absent arrangement details, and contradictory schedule statements. Invalid/unusable input must fail clearly; missing/conflicting arrangement details must remain explicit uncertainty in an otherwise valid assessment. System fixtures additionally cover refusal, usage limits, interrupted streams, and invalid evidence. None of these checks should fetch a job URL.

For sign-out, use `uv run --locked job-scan auth logout`; verify local secrets are removed and the command distinguishes confirmed from unconfirmed remote revocation.

For user/worker VMs, use the encrypted registration handoff documented in [evaluations/README.md](../../evaluations/README.md); the worker runs evaluations after import. Candidate geography, eligibility and time-zone details are outside this work-arrangement criterion.
