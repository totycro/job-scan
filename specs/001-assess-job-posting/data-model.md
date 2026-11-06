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

Each shared case contains `posting.html`, `metadata.json`, unchanged `owner-note.txt`, and `expected.json`. Preserve substantive job/company content and meaningful structure so future features can annotate the same input. Metadata records provenance, capture/transformations, content-review status and the exact input hash. The corpus currently contains three rich generic drafts; it is not yet an approved dataset.

`expected.json` contains `schema_version`, `case_id`, and `criteria`. Each criterion key owns its review status, authorship, posting hash, expected semantic field values, required findings/uncertainties, evidence quotes/occurrences, and prohibited conclusions. Only `work_arrangement` is currently annotated. Its owner-authored short notes are retained; expanded checks remain agent proposals pending owner review.

An absent criterion key means not annotated/not evaluated; an explicit expected `not_stated` or `null` means a checked absence in the source. Omitted expected fields are not checks. A changed posting hash invalidates prior review until the owner checks the content and each existing criterion against the new version. Evaluation must report pending/stale/missing annotations rather than counting them as passes. See the [corpus lifecycle](../../evaluations/cases/README.md) for review and growth toward roughly ten representative postings.

A developer evaluation run records timestamp, Git revision, selected case/criterion keys, input/expectation/prompt/schema hashes, requested and returned model identity when available, reasoning settings, per-case findings/evidence results, manual relevance review, and limitations. Feature acceptance requires its selected coverage and all mandatory expectations to pass with approved content/criterion reviews. Reports remain separate from product output. Keep focused edge-case fixtures, including the SC-002 structure-sensitive pair, separate from the shared rich postings.

## OAuth Session (provider infrastructure)

Protected runtime record holds stable host ID, issued client IDs, verified identities, token/scopes/expiry, and active registration. Follow the reference's per-registration storage and refresh semantics with a separate job-scan directory. Never include credential values in assessment models, fixtures, reports, logs, or source control. Authentication transitions are signed out, authorization pending, authorized with/without plan permission, refresh required, and revoked/expired; only authorized plan permission allows inference.
