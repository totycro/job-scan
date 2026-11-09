# job-scan

A personal CLI that assesses work arrangements in saved job-posting HTML using ChatGPT.
It reports source facts, exact supporting excerpts and locations, preference-based fit,
and missing or conflicting information. Remote is preferred; hybrid is acceptable. Candidate residence, right-to-work/visa and time-zone requirements belong outside this criterion.

The first increment assesses one saved UTF-8 HTML file up to 256 KiB. It preserves
HTML structure and sends the intact file to the signed-in account's model. An optional
source URL records provenance and is never fetched. Company research, commute estimates,
scores, application decisions, and saved-report management are outside this increment.

## Setup and use

Requires Python 3.14, uv, and Linux/macOS.

Run from the repository root:

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

Commands and options are declared with Typer. Use `job-scan --help`,
`job-scan assess --help`, or `job-scan auth --help` to explore the interface.

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

Personalized ratings accept an explicitly selected TOML file:

```bash
mkdir -p .local
cp examples/preferences.toml .local/preferences.toml
# Edit .local/preferences.toml before running:
uv run --locked job-scan assess posting.html --profile .local/preferences.toml
```

The starter is intentionally incomplete. Enter your own prose for at least one dimension:
role fit (responsibilities/seniority), technology fit (known versus desired, avoided or
willing-to-learn technologies), field interest (business domain), and company affinity
(employer identity/practices). Every dimension needs importance 1–5; it weights the mean,
while absent or blank preferences skip assessment. Relevant configured text is sent to
the assessment model. The file is read once and never rewritten; paths and hashes stay local.

Optional exceptions reference an exact excerpt already in the preferences:

```toml
[[dimensions.technology_fit.exceptions]]
id = "avoid-php"
kind = "deal_breaker"
preference_quote = "I will not work in a role requiring PHP."
```

Use `compelling_attraction` for a preference that warrants pursuing despite weaknesses.
Include the quoted sentence in that dimension's prose first. See the completed fictional
[profile example](specs/002-personalized-job-ratings/contracts/profile.example.toml).
Exceptions affect a separate decisive outcome; they never add points or change weights.
Scores are subjective fit, not probabilities. The weighted mean covers only rated configured
dimensions; partial results disclose missing dimensions and coverage. Work arrangement
remains qualitative alongside the four new outcomes. HTML supplies all factual evidence;
company names, profile beliefs and omitted technologies do not establish additional facts.

Personalized inference runs work arrangement, fit, and optional exceptions sequentially,
then emits one complete report. The maximum inference budget is 360 seconds without
exceptions or 540 seconds with them, excluding authentication. There is no automatic retry
or billing fallback. If no configured dimension can be rated, the report shows no numeric
overall score. Confirmed opposing exceptions produce “conflicting exceptions” with evidence
for both; unresolved declarations remain visible alongside any confirmed outcome.
