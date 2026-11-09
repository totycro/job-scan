# Evaluation Contract: Posting/Profile Pairs

**Status**: Proposed extension to the existing developer runner, not a new product interface. New commands below become available during implementation.

## One manifest and backward compatibility

Use one automatically loaded `evaluations/manifest.json` for every required case. Do not add a manifest-path option or a second manifest. Preserve the existing offline/live/review commands; each run evaluates the complete required list, covering both existing work-arrangement behavior and the new personalized behavior.

Migrate the current manifest to `schema_version: 2` with a single `required_cases` array. Each entry has exactly:

- `id`: stable unique review key. Preserve existing posting-path IDs such as `cases/posting-01` for migrated cases; assign distinct IDs to new posting/profile pairs.
- `mode`: `work_arrangement` or `personalized`.
- `posting`: saved HTML path relative to `evaluations/`.
- `profile`: null for work-arrangement mode; required profile path for personalized mode, relative to `evaluations/`.
- `expectations`: expectation file path relative to `evaluations/`.

Examples of entries in the same required list:

```json
[
  {
    "id": "cases/posting-01",
    "mode": "work_arrangement",
    "posting": "cases/posting-01/posting.html",
    "profile": null,
    "expectations": "cases/posting-01/expected.json"
  },
  {
    "id": "climate-php-conflict",
    "mode": "personalized",
    "posting": "personalized/climate-php/posting.html",
    "profile": "profiles/climate-php.toml",
    "expectations": "personalized/climate-php/expected.json"
  }
]
```

Dispatch validation and assessment by each entry's typed mode; there is no manifest-wide criterion/mode selector. A posting may appear in multiple entries with contrasting profiles. Duplicate/missing required IDs, unknown modes, missing personalized profiles, and work-arrangement entries with a profile fail readiness. Source-content metadata remains beside each posting (`metadata.json`) and is reusable across entries only while its posting hash matches. Preserve existing work-arrangement corpus, expectation format, and request payloads; migrate tests that assumed string-only manifest entries. Legacy run approvals are not transplanted into a changed full-suite run.

## Expected outcomes

Personalized expectation files have `schema_version`, `case_id` matching the pair ID, `posting_sha256`, `profile_sha256`, `review_status` (`approved` or `pending_owner_review`), `expectation_authorship`, and a `criteria` map. Each evaluated new criterion includes expected state, required semantic findings, prohibited conclusions, supporting exact source evidence, required preference excerpts, and expected exception applicability keyed by declaration ID. Specify expected overall availability and decisive outcome separately. Wrong/unknown expectation fields fail readiness rather than silently imposing no check.

Assertions are manually authored. Supported state/evidence/exception assertions can be checked automatically. Optional manually justified broad score bands or contrasting-pair relative direction can capture a desired material fit distinction; no exact-score or exact-prose oracle. Explicit expected insufficient/unresolved states are assertions; missing annotations mean not evaluated, never checked absence. Work-arrangement expectations remain in their existing format and baseline corpus; a personalized report's work findings must also respect those boundaries.

Readiness validates files, profile schema, source/profile hashes, source-content review, expectation authorship/review status, known dimension/declaration IDs, evidence references, manifest coverage, and each spec-defined coverage group. It performs no authentication or inference. Pending/stale reviews are reported and never counted as acceptance. A run cannot succeed by selecting a subset of mandatory pairs.

## Automatic and semantic checks

Automatic checks cover strict response schemas, exact enabled-dimension/exception coverage, posting quote resolution, profile substring references, absence of model-invented weights/outcomes, disabled semantics, weighted arithmetic/display precision, withheld overall scores, and deterministic decisive-outcome reduction. Request-contract tests independently compare fit payloads when only positive weights or exception metadata change; zero-weight toggles legitimately change the requested set.

Owner review establishes semantic interpretation, evidence relevance/attribution, missing/conflicting information, required/prohibited judgments, comparative profile behavior, and report usefulness. Quote existence alone is insufficient. Every mandatory pair needs owner review bound to its run; model-generated expected findings or fabricated approvals are forbidden.

Mandatory coverage: contrasting profiles for each of the four new dimensions; knowledge versus learning/avoidance; field interest separate from affinity; employer versus agency/client facts; absent/contradictory evidence; HTML associations; untrusted instructions; undeclared ordinary preferences; compelling attraction; deal-breaker; both types within and across dimensions; unknown exception applicability with and without other confirmed matches; zero/low-weight exception handling; incomplete numeric aggregates; all three request-stage failures; preserved baseline work-arrangement findings. Offline input/privacy/request invariants complement the live corpus.

## Result and review binding

Use each manifest entry ID as its manual-review key. Existing work-arrangement IDs remain posting paths; personalized entries have unique pair IDs. One review file binds every required entry in the same run. Record:

- Original posting/profile bytes' hashes, profile schema version, expected/metadata/manifest hashes, required case IDs and their modes, source/lockfile revision hashes, and effective prompt/schema hashes for every stage.
- Requested/returned model, reasoning, stage timings, outcome/failure, validated results, rendered report, automatic checks, and limitations.
- Immutable run ID calculated from the complete unreviewed run, plus an owner-authored review file referring to that exact ID and all required pair IDs.

Revalidate all bound hashes when applying review, including profile bytes and the single manifest. Missing/stale profiles or changed code/configuration invalidate approval. Record no raw OAuth secrets, callbacks, or personal user profiles. Developer evaluation outputs live under ignored `.local/evaluations/`; checked-in profiles/recordings contain fictional content only. Existing review booleans (`semantic_findings`, `evidence_relevance`, `prohibited_conclusions_absent`, `report_usable`) remain and cover the new typed results.

## Commands and acceptance

```bash
uv run --locked python evaluations/run.py --check --output .local/evaluations/readiness.json
uv run --locked python evaluations/run.py --live --recordings-dir tests/recordings/inference --output .local/evaluations/latest.json
uv run --locked python evaluations/run.py --review .local/evaluations/latest.json --manual-review .local/evaluations/manual-review.json --output .local/evaluations/reviewed.json
```

Review mode checks the original run against the current single manifest and requires exactly its full set of case IDs; it makes no inference calls. Missing, extra, or stale case coverage cannot establish acceptance. Keep exit 0 only for completed mandatory automatic checks and valid accepted review; pending review/readiness failures exit 1. `--check` can report readiness but cannot claim live acceptance. No live calls run automatically as part of routine tests. Work-arrangement regressions and personalized pairs are evaluated together; no mode filter or partial-suite acceptance is introduced.

Reuse sanitized actual inference SSE recording support for every required stage. Match replay requests by method/URL/body hash, not pair path alone. Existing work-arrangement requests keep their exact body serialization so their cassettes can be reused. New fit/exception recordings are required for successful personalized system paths; synthetic exceptional-response tests are not live quality evidence. Refresh baseline live review when code hashes change, even when old baseline recordings remain valid for offline replay.
