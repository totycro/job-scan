# Data Model: Personalized Job Ratings

**Status**: Design contract; no persistence migration. Reuse the strict Pydantic base (`strict=True`, `extra="forbid"`) and existing `Evidence`/`ResolvedEvidence`. Provider schemas use objects/arrays with explicit required fields and nullable values; cross-field invariants are also checked locally.

## Profile and dimension identity

| Entity | Fields | Constraints |
| --- | --- | --- |
| ProfileInput | local path, SHA-256 of original bytes, parsed Profile | Read once per invocation; no mutation; path/hash remain local |
| Profile | `schema_version: 1`, `dimensions: mapping[str, DimensionProfile]` | Exactly the four supported new IDs in version 1; no extra root fields |
| DimensionProfile | `importance: int`, `preferences: str`, `exceptions: list[ExceptionDeclaration]` | Weight 0–5; no coercion from booleans, floats, or strings; preferences/exceptions may default to empty only when disabled; enabled prose must contain non-whitespace; at least one profile dimension enabled |
| ExceptionDeclaration | `id: str`, `kind: compelling_attraction \| deal_breaker`, `preference_quote: str` | IDs unique across profile, match `[a-z][a-z0-9_-]{0,63}`; nonblank quote must be an exact contiguous substring of that dimension's preferences; no duplicate `(kind, preference_quote)` in a dimension |
| DimensionDefinition | stable ID, label, prompt fragment | Static code-owned definitions, ordered presentation; no runtime plugin loading |

Current new IDs: `role_fit`, `technology_fit`, `field_interest`, `company_affinity`. Existing dimension ID: `work_arrangement`. Version 1 of this profile supports the four additions only; the product dimension vocabulary is not capped at four or five. A future feature explicitly adds a supported definition and decides profile-version compatibility.

If an exception excerpt appears multiple times in the same prose it still identifies one declaration; no profile occurrence counter is needed. Treat prose as user preferences, not as verified company facts or instructions overriding application rules. Parse/validate even disabled definitions and any supplied declarations, but do not send their content or evaluate them. Zero-importance entries need not include prose or declarations.

## Fit request projection

`FitInput = {html: str, dimensions: [{dimension_id: str, preferences: str}]}` in definition order, enabled entries only. No profile path, file hash, importance, or exceptional declaration metadata enters this projection. Keep preference text intact. Equal HTML, enabled-ID set, preference text, model/configuration, prompts, and schema produce equal serialized scoring requests; adjusting only positive importance values or declaration metadata cannot change that request. Setting a weight to zero changes the enabled set and therefore the request.

## Model fit response

`FitResponse` has `dimensions: list[DimensionFit]`. There must be exactly one entry for each requested enabled ID, no unknown/disabled/duplicate/missing IDs. Model-returned order is normalized locally. Missing entries are invalid output, not insufficient evidence.

| Entity | Fields | Invariants |
| --- | --- | --- |
| DimensionFit | `dimension_id`, `status`, `score`, `explanation`, `findings`, `judgments`, `uncertainties`, `conflicts` | `status` is `rated` or `insufficient_evidence`; explanation nonblank; all fields required in provider response |
| SourceFinding | `id`, `statement`, `evidence: list[Evidence]` | ID unique within dimension; statement nonblank; at least one valid source quote; factual assertions belong here |
| PreferenceJudgment | `preference_quote`, `finding_ids: list[str]`, `polarity: match \| mismatch \| mixed`, `explanation` | Quote is exact substring of requested dimension prose; finding IDs exist in that dimension and list is nonempty; explanation nonblank; expresses inference rather than an additional unsupported fact |
| Conflict | existing `explanation`, `evidence` | Preserve existing requirement for at least two supporting passages; retain conflicting context |

For `rated`, score is a strict integer from 0 through 100, with at least one source finding and preference judgment. Scores express subjective fit (0 no fit, 50 mixed, 100 full), never probability. For `insufficient_evidence`, score is null and at least one uncertainty or conflict explains why; supported partial findings/judgments may remain. Every supplied evidence quote is checked even for an unrated dimension. Missing information is described as uncertainty, never as an invented source quote or a fabricated mismatch. A dimension MAY be rated from partial evidence only when the explanation supports a dimension-level fit judgment using the evidenced preferences without assuming facts about unassessed preferences. It MUST identify the supported and unassessed preferences and explain why the missing or conflicting information does not prevent that judgment. If a score would require assuming how an unassessed preference is satisfied or resolving an unsupported conflict, the dimension MUST be `insufficient_evidence`, retaining supported findings but no score. A source quote and a preference match alone do not establish sufficiency. This is a qualitative semantic-review rule, not a numeric preference-coverage threshold. Apply the paired examples in spec US3 scenario 2 during golden semantic review; schema validity and quote existence cannot decide sufficiency alone.

Every `Evidence` uses exact raw HTML `quote` and zero-based `occurrence`, counting overlapping matches. Resolve with existing `resolve()` into character start/end and line/end-line, and deduplicate by `(quote, occurrence)`. Relevance, employer/role attribution, entailment, and appropriate scoring require semantic review beyond quote existence.

## Exception matching

`ExceptionInput = {html: str, exceptions: [{dimension_id, exception_id, kind, preference_quote}]}` for enabled declarations only. This request sees no weights or numeric scores. The locally validated profile is authoritative for IDs, types, and quotes.

`ExceptionResponse = {exceptions: list[ExceptionMatch]}` with exactly one result per requested declaration and no extras. A match contains `exception_id`, `status: matched | not_matched | unresolved`, nonblank `explanation`, and `evidence: list[Evidence]`. Matched/not-matched claims require at least one supporting quote. Unresolved entries may have no quote or may include conflicting evidence, but must explain uncertainty. Absence of a named technology in the posting is not evidence of absence. Unknown IDs, duplicates, missing results, invalid quotes, or unsupported status/shape fail validation. Do not accept model-returned weights, exception types, or final outcomes.

Empty enabled declaration set skips this request and produces a local empty collection. An exceptional declaration references ordinary preference text; toggling its kind or adding/removing the declaration changes only exception processing, not ordinary scoring input.

## Local dimension and aggregate outcomes

`DimensionOutcome` combines dimension ID, importance, state (`rated`, `insufficient_evidence`, or locally created `disabled`), nullable score, findings/judgments/uncertainties/conflicts, resolved evidence, and its exception matches. Disabled entries have weight zero, null score, no computed findings, and no evaluated exceptions.

`WeightedOverall` contains `status: available | partial | unavailable`, nullable integer numerator/denominator, nullable Decimal value, `missing_dimension_ids`, rated/enabled dimension counts, rated/total enabled importance, and a contribution list. `available` means all enabled dimensions are rated; `partial` means some but not all are rated; `unavailable` means none is rated. For available or partial aggregates:

- Numerator = sum of `importance * score` for every rated positive-weight new dimension.
- Denominator = sum of rated enabled dimensions' importance; greater than zero when at least one dimension is rated.
- Contribution per rated enabled dimension = `importance * score / denominator`; preserve unrounded values.
- Display Decimal value rounded half up to one decimal; do not sum pre-rounded display contributions.
- Report inputs/numerator/denominator so users can verify totals. Independently rounded displayed contributions may differ by a tenth from the final rounded sum; label them approximate.

If some enabled dimensions are unrated, retain their null scores and list each missing dimension and its reason. Calculate the mean and contributions over rated enabled dimensions only and label it partial. Show rated/enabled dimension counts and rated/total enabled importance so the excluded weight is explicit. If none is rated, status is unavailable: numerator, denominator, and value are null, contributions are empty, and all missing dimensions remain visible. Disabled dimensions are excluded from both coverage totals. Work-arrangement findings never enter this aggregate.

Fixed example: role 80 at importance 2, technology 60 at importance 1, and company affinity unrated at importance 3 (field disabled) gives numerator 220, denominator 3, and “Partial overall: 73.3/100; 2/3 enabled dimensions rated; importance coverage 3/6; company affinity missing.” The missing dimension does not receive a score.

## Decisive outcome

Reduce confirmed matches using the declaration types from the profile:

| Matched compelling attraction | Matched deal-breaker | Any unresolved | Outcome |
| --- | --- | --- | --- |
| Yes | Yes | Either | `conflicting_exceptions` — conflicting exceptions |
| Yes | No | Either | `worth_pursuing_despite_weaknesses` — worth pursuing despite weaknesses |
| No | Yes | Either | `deal_breaker` — deal-breaker |
| No | No | Yes | `unresolved_exceptions` — unresolved exceptions |
| No | No | No | `no_exception_applies` — no exceptional preference applies |

`DecisiveOutcome` includes code, matched declaration IDs, unresolved declaration IDs, and references to their explanations/evidence. Render matched-based outcomes as based on confirmed matches only when unresolved declarations remain. Neither importance nor dimension membership resolves opposing matches. This outcome can exist with a partial or unavailable numeric aggregate. It is user guidance, not an automatic application action.

## Composite result and lifecycle

`PersonalizedAssessment` contains the existing `Assessment` (source, unchanged work-arrangement findings/fit/evidence/model), profile identity, ordered new `DimensionOutcome` collection, `WeightedOverall`, `DecisiveOutcome`, and per-pass requested/returned model/configuration metadata. The report therefore identifies five dimensions in this increment without coercing work arrangement into a scored type.

Invocation lifecycle: local read → profile/posting validation → work-arrangement completion and validation → fit completion and validation → optional exception completion and validation → pure assembly → render/emit once. Any stage failure yields no successful report. Unknown evidence states advance normally. Inputs/results are in memory for the invocation; no product report database, cache, or profile lifecycle beyond user file edits.

## Golden posting/profile pair

One versioned evaluation manifest contains a required list of cases with stable ID, mode (`work_arrangement` or `personalized`), posting reference, nullable profile reference, and expectation reference. Work-arrangement entries have no profile; personalized entries require one. Existing posting-path IDs are preserved when migrating the baseline entries. A `PersonalizedGoldenCase` adds pair-specific manually authored expectations, content/expectation review status, and current input hashes. Expected assertions cover dimension states, semantic matches/mismatches, qualitative comparative score direction or broad owner-authored bands where useful, exception statuses, aggregate availability, and decisive code. Omitted assertions impose no requirement; explicit unknown states are checked absence of usable evidence. Expected prose and exact scores are not generated by a model.

Review binding includes both input hashes, all effective prompt/schema versions and hashes, requested/returned model per pass, the single manifest/expectation/code/lockfile hashes, and immutable run ID. Stale or pending review is not acceptance. See [contracts/evaluation.md](contracts/evaluation.md).
