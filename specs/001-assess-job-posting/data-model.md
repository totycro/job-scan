# Data Model: Assess a Job Posting

**Status**: Proposed implementation contracts; no database or runtime assessment persistence.

## PostingInput

- `path`: local file identity; `source_url`: optional HTTP(S) provenance, never fetched.
- `html`: exact UTF-8 decoded content; `sha256`: hash of original bytes.
- Validate a readable regular file, nonempty UTF-8 (optional BOM accepted), and at most 262,144 bytes. Do not normalize whitespace, strip markup, or silently truncate. The model identifies whether the content contains a usable posting.

## Evidence

- `quote`: nonempty exact contiguous substring of `html`; markup is permitted.
- `occurrence`: zero-based index among occurrences of that exact substring, counted by increasing start position (including overlapping matches).
- `start`, `end`: half-open Unicode character offsets computed locally from the selected occurrence; line numbers are derived for display, not supplied by the model.
- Reject unmatched quotes and out-of-range occurrences. Keep the original excerpt available in the report. Cite additional context when a heading or table association matters.
- Validating a match proves provenance, not that the evidence supports the interpretation; golden expectations cover that distinction.

## WorkArrangementResult

Strict Pydantic response model; disallow unknown keys and type coercion.

- `posting_status`: `identified | ambiguous | absent`. Ambiguous/absent produces failure, with a short explanation.
- `arrangements`: list of findings, each containing `kind` (`remote | hybrid | onsite`), `context` (role/location/options/conditions), and one or more evidence entries. Multiple alternatives are allowed; an empty list means no arrangement was established.
- `home_working`: schedule findings with `days_text` and `period` (nullable strings preserving the stated quantity/range and period), `kind` (`allowed | expected | unspecified`), `context`, and evidence. `unspecified` has null quantity/period and does not claim a fabricated absence quote.
- `uncertainties`: missing-information explanations; `conflicts`: explanations with the evidence for opposing statements.

Positive arrangements, quantities, restrictions, and conflict statements need source evidence. Missing information is explicitly labelled as absence, not represented as an invented source statement. Home-working `days_text` must reproduce the cited wording; do not silently calculate days from office-attendance statements. An allowed/expected schedule may have null quantity when wording is qualitative; explain that uncertainty.

## Assessment

Contains the validated source findings, resolved evidence, and locally derived fit judgments. Remote maps to preferred; hybrid to acceptable; on-site to outside the stated preferences. Missing/conflicting findings remain uncertain, and available alternatives retain their conditions. No score, hard rejection, personal-eligibility inference, or overall application recommendation.

Flow: `input validated → complete model response → schema/evidence validated → preferences applied → report`. Any failed step yields an explanatory unsuccessful command outcome; never display a completed report from partial output.

## GoldenCase and EvaluationRun

Each versioned case contains `posting.html` and manually authored `expected.json`: case ID, required findings/uncertainties, expected evidence/associations, and prohibited conclusions. Expectations may match structured fields and supporting spans without demanding identical report prose. Include the paired HTML association example from SC-002. These cases have not yet been authored.

A developer evaluation run records timestamp, Git revision, case/prompt/schema hashes, requested and returned model identity when available, reasoning settings, per-case findings/evidence results, manual relevance review, and limitations. Keep reports separate from product output. A failed mandatory expectation fails acceptance.

## OAuth Session (provider infrastructure)

Protected runtime record holds stable host ID, issued client IDs, verified identities, token/scopes/expiry, and active registration. Follow the reference's per-registration storage and refresh semantics with a separate job-scan directory. Never include credential values in assessment models, fixtures, reports, logs, or source control. Authentication transitions are signed out, authorization pending, authorized with/without plan permission, refresh required, and revoked/expired; only authorized plan permission allows inference.
