# Quickstart Validation: Personalized Job Ratings

**Status**: Post-implementation validation guide. The new profile flag, shipped starter, personalized corpus and unified manifest schema described here are planned interfaces, not functionality already implemented by the planning step.

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
