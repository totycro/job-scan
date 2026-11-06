# job-scan

A personal CLI that assesses work arrangements in saved job-posting HTML using ChatGPT.
It reports source facts, exact supporting excerpts and locations, preference-based fit,
and missing or conflicting information. Remote is preferred; hybrid is acceptable. Candidate residence, right-to-work/visa and time-zone requirements belong outside this criterion.

The first increment assesses one saved UTF-8 HTML file up to 256 KiB. It preserves
HTML structure and sends the intact file to the signed-in account's model. An optional
source URL records provenance and is never fetched. Company research, commute estimates,
scores, application decisions, and saved-report management are outside this increment.

## Setup and use

Requires Python 3.14, uv, and Linux/macOS. Install from the repository root:

```bash
uv sync --locked
uv run --locked job-scan auth login
uv run --locked job-scan models
uv run --locked job-scan assess evaluations/cases/posting-01/posting.html
uv run --locked job-scan assess posting.html --source-url https://example.com/job
```

Sign-in uses the browser and ChatGPT plan permission, with no API-key billing fallback.
The default is `gpt-6.1-sol` with low reasoning; `--model MODEL` selects another account-
available model. Unsupported models and exhausted plan limits produce explanatory failures.
Credentials are stored privately under `$XDG_CONFIG_HOME/job-scan/` or `~/.config/job-scan/`.
Use `auth status`, `auth use REGISTRATION_ID`, and `auth logout` to manage registrations.
Status does not refresh credentials. Login waits in the foreground for up to 15 minutes.

Inference has a 180-second total deadline and 10-second connection timeout. Reports appear
only after stream completion and schema/evidence validation. Missing arrangement details
produce uncertainty; absent/ambiguous postings and invalid responses produce failures.

Exit codes: 0 successful assessment/auth/help; 1 assessment/auth/provider failure;
2 invalid arguments/input; 130 interrupted. Failures use stderr without a success report.

## Development and validation

```bash
uv run --locked ruff check src tests evaluations
uv run --locked ruff format --check src tests evaluations
uv run --locked ty check src tests evaluations
uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90
```

The suite substitutes external HTTP traffic and blocks unrecorded sockets. Successful
system assessments replay sanitized actual-provider SSE; synthetic failures test exceptional
paths. Missing actual recordings fail system tests with the case name and expected path.
The coverage gate is 90% combined statements and branches, including auth and transport.

Manually authored cases and expectations are the golden guardrail. Live semantic validation
is separate from coverage and replay:

```bash
uv run --locked python evaluations/run.py --check --output .local/evaluations/readiness.json
uv run --locked python evaluations/run.py --live --recordings-dir tests/recordings/inference --output .local/evaluations/latest.json
```

An evaluation remains unsuccessful until all automatic checks and bound owner reviews pass.
See [evaluation workflow](evaluations/README.md), [feature validation](specs/001-assess-job-posting/validation.md),
and [Spec Kit guide](SPEC_KIT_GUIDE.md). Reports and credentials are not versioned.
