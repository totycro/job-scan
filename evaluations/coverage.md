# Feature acceptance coverage and review matrix

The owner approved all shared source-content reviews and all focused fixture content/expectations on 2026-11-06. Existing shared criterion expectations remain approved. Live results and their manual semantic reviews are recorded separately in `.local/evaluations/`. A successful run
requires every entry in `manifest.json` plus manual semantic/evidence/usability review.

| Requirement/scenario | Cases or checks |
| --- | --- |
| FR-001 / scenario 6 / SC-003 input failures | tests/unit/test_cli.py; loading, ambiguous |
| FR-002 / scenario 5 / SC-002 | posting-03 related cards; structure-pair/allowed and expected |
| FR-003 / scenarios 1,4 | posting-02, posting-03; remote-restrictions |
| FR-004 / scenario 2 | hybrid-allowed, hybrid-expected, qualitative, posting-01 |
| FR-005 / SC-001 evidence | all cases; test_evidence.py; manual source relevance review |
| FR-006 / scenario 3 | missing, conflict, flexible, office-days |
| FR-007 / SC-004 usability | all successful reports; manual owner review |
| Unusable source / loading shell | loading |
| Office-day arithmetic | office-days |
| Untrusted page instructions | untrusted-instructions |

The structure pair retains identical text in identical order and changes only the HTML
associations (`aria-labelledby`). It must produce different target-role schedules.

Pending reviews do not prevent independent coding. They cannot establish acceptance.
Never approve source or criterion metadata automatically or copy inference into expectations.

## Feature 002 implementation and pending acceptance

The single version-2 manifest contains 16 preserved baseline entries and 31 new fictional
posting/profile pairs. The owner approved all 31 new source-content and semantic expectations in conversation.
The owner explicitly approved all 47 actual results for the current immutable run.
Historical feature-001 approvals do not approve a changed full-suite run. Deterministic tests
and request replay cannot establish semantic correctness. Every new successful CLI replay
requires actual sanitized provider streams; all current streams have been captured and replayed successfully.

| Requirement | Required pair groups / artifacts | Deterministic verification |
| --- | --- | --- |
| FR-001 | All personalized pairs; legacy corpus | `tests/unit/test_cli.py`, `tests/system/test_recorded_success.py` |
| FR-002 | All four contrast groups; empty preference dimensions | `tests/unit/test_profiles.py`, `tests/unit/test_rating_requests.py`, `tests/unit/test_ratings.py` |
| FR-003 | `examples/preferences.toml`, README, quickstart starter-edit scenario | Installed help and fictional starter-edit workflow checks passed |
| FR-004 | Strict types, all blank, invalid declarations, size/BOM/UTF-8 and immutable input | `tests/unit/test_profiles.py`, `tests/unit/test_cli.py` |
| FR-005 | Eight contrast pairs; subjective scale | `tests/unit/test_rating_models.py`, `tests/unit/test_personalized_report.py`; bound owner review approved |
| FR-006 | Evidence-gap and attribution pairs below | `tests/unit/test_ratings.py`, `tests/unit/test_personalized_report.py`; bound FR-006 sufficiency review approved |
| FR-007 | `partial-overall`, `all-unknown`; fixed weighting checks | `tests/unit/test_ratings.py` checks equal/unequal/reversed weights, monotonicity, rounding and exact coverage |
| FR-008 | Attribution, structure and untrusted pairs below | `tests/unit/test_rating_requests.py`, `tests/unit/test_ratings.py`; bound owner factual entailment review approved |
| FR-009 | All pairs; report identity, all five dimensions | `tests/unit/test_personalized_report.py`, `tests/system/test_personalized_cli.py` (actual replay passed) |
| FR-010 | Invalid local inputs; all three stage failures | `tests/unit/test_cli.py`, `tests/system/test_personalized_failures.py` |
| FR-011 | Relevant excerpts, local provenance, safe failures | `tests/unit/test_rating_requests.py`, `tests/unit/test_cli.py`, `tests/unit/test_personalized_report.py` |
| FR-012 | One full manifest/run/review, review index and all new pairs | `tests/unit/test_evaluations.py`; actual source and result reviews approved |
| FR-013 | All exception pairs, absent/empty declarations, invalid excerpt tests | `tests/unit/test_profiles.py`, `tests/unit/test_exceptions.py`, `tests/unit/test_rating_requests.py` |
| FR-014 | Every decisive code, unresolved alongside matches, low weights | `tests/unit/test_exceptions.py`, `tests/unit/test_personalized_report.py`; bound owner review approved |
| FR-015 | Work arrangement preserved plus four code-owned definitions; iterated mechanics | `tests/system/test_recorded_success.py`, `tests/unit/test_ratings.py`, `tests/unit/test_personalized_report.py` |
| SC-001 | Starter-edit/help, all contrast pairs, profile identity | Help, input, fictional starter-edit and actual replay checks passed |
| SC-002 | All contrast, attribution, structure and untrusted pairs | Full required findings/prohibited conclusions/evidence relevance passed bound owner semantic review |
| SC-003 | Fixed equal/unequal/reversed weights and skipped dimensions | `tests/unit/test_ratings.py`, `tests/unit/test_rating_requests.py` |
| SC-004 | `partial-overall`, `all-unknown`, both partial-preference examples, conflicts | `tests/unit/test_ratings.py`, `tests/unit/test_personalized_report.py`; actual replay and bound review passed |
| SC-005 | All invalid-profile and work/fit/exception failure variants | `tests/unit/test_cli.py`, `tests/system/test_personalized_failures.py` |
| SC-006 | All 16 legacy IDs, no profile and excluded work score | Actual baseline replay passes; current full-suite live acceptance passed |
| SC-007 | All exception pairs; declaration/weight-only request invariance | `tests/unit/test_exceptions.py`, `tests/unit/test_rating_requests.py`, `tests/unit/test_ratings.py`; live semantic acceptance passed |
| SC-008 | Named work arrangement plus four new outcomes | `tests/unit/test_personalized_report.py`, `tests/system/test_personalized_cli.py` (actual replay passed) |

### Exact required personalized pair coverage

All source/profile/expectation links are in [the owner review index](personalized/README.md).

| Pair IDs | Coverage |
| --- | --- |
| `role-contrast-high`, `role-contrast-low` | Desired responsibilities versus management; same facts, contrasting role preferences |
| `technology-contrast-high`, `technology-contrast-low` | Known versus desired/avoided tools and learning Rust; explicit absence of PHP |
| `field-contrast-high`, `field-contrast-low` | Business-domain interest independent of employer practices |
| `affinity-contrast-high`, `affinity-contrast-low` | Employer-practice preference independent of business field |
| `attraction-despite-weaknesses` | Low-importance attraction with weak heavily weighted role/technology fit |
| `breaker-despite-strengths` | Low-importance breaker despite heavily weighted strengths |
| `ordinary-undeclared` | Explicit empty declaration arrays; ordinary dislikes do not become exceptions |
| `opposing-across-dimensions`, `opposing-same-dimension` | Both kinds match; weights never choose a winner |
| `unresolved-only` | Unresolved exception with no confirmed matches; partial total |
| `unresolved-plus-attraction`, `unresolved-plus-breaker`, `unresolved-plus-both` | Unknown conditions remain alongside confirmed-match-only outcomes |
| `unavailable-with-attraction` | Supported exceptional excerpt with no supported dimension-level score |
| `exception-omitted-unresolved` | Omitted Rust remains unresolved, never disproved by silence |
| `exception-explicit-not-matched` | Explicit source statement disproves a PHP requirement |
| `partial-optional-rated`, `partial-required-unknown` | Both FR-006 / US3 scenario-2 examples: optional unknown versus required condition |
| `partial-overall` | Rated-only denominator, missing dimension and dimension-count/importance coverage |
| `all-unknown` | Null overall numerator/denominator/value and no contributions |
| `conflicting-responsibilities` | Both target-role passages retained; required condition unresolved |
| `omitted-technology` | No absence inference from a missing PHP mention |
| `agency-client-separation` | Agency field/benefits do not transfer to employer |
| `company-name-beliefs` | Explicit named-employer preference, unverified reputation and unknown field |
| `structure-backend`, `structure-management` | Identical text/order, changed HTML associations; relative direction assertion |
| `untrusted-profile-instructions` | Embedded score/benefit commands do not override source-only evidence policy |

### Quickstart and verification boundaries

Profile input/privacy/help scenarios use `tests/unit/test_cli.py`, `tests/unit/test_profiles.py`,
`tests/unit/test_rating_requests.py`, and `tests/system/test_entrypoint.py`. Starter-edit and
human report usability remain actual owner checks. Synthetic HTTP failure tests reach every
work/fit/exception boundary (HTTP/schema/quote/incomplete/refusal/timeout/registration/interruption)
and assert empty stdout and safe diagnostics. `test_personalized_cli.py` covers two/three ordered
requests, all named dimensions, complete/partial/unavailable scores, exception evidence and
successive contrasting profiles, and passes with the actual recordings captured by T054.
Missing annotations, pending reviews and stale hashes never count as accepted cases.

Current acceptance: run `b1d1383f7a6856baf98353aa9b9133bc0455ead4951eb5bf26d732eb31aa0486`, 47 automatic passes, 298 offline test passes, 98.04% coverage, and explicit bound owner review (`accepted=true`). See the final validation section in the feature quickstart.
