# CLI Contract: Personalized Assessment

**Status**: Proposed interface to implement. Existing commands and no-profile behavior remain supported.

## Invocation

```text
uv run --locked job-scan assess POSTING [--profile PROFILE] [--source-url URL] [--model MODEL]
```

`POSTING`, `--source-url`, `--model`, auth commands, and model discovery preserve their existing contracts. Add only the optional `--profile PATH` flag to `assess`; relative paths resolve against the invocation directory. No interactive questionnaire or profile discovery occurs. Document `--profile` in Typer help and README. There is no command that automatically modifies profile files.

Without `--profile`, run the original work-arrangement request, validation, and terminal report with its current preference policy. With `--profile`, validate the saved HTML and [profile](profile.md) before constructing auth/network clients, then run the required stages described in [plan.md](../plan.md). Profile validity is required only for personalized mode. The source URL records provenance and is never fetched.

## Successful terminal output

Emit one complete report to stdout, after all requests and validation. Include:

1. Posting file and optional source URL, selected profile file, and model information per request stage.
2. Work-arrangement dimension with the existing arrangement, home-working schedule, evidence, qualitative fit, uncertainty, and conflicts. It has no numeric score or profile weight in this increment.
3. Four separately named new dimension sections: role fit, technology fit, field interest, company affinity. Show each configured dimension's importance, score or insufficient-evidence state, relevant preference excerpts, supported matches/mismatches, source evidence with resolved locations, and uncertainty/conflicts. Show dimensions with absent/blank preferences as not configured and skip their fit requests and numeric contributions. Evaluate every supplied valid exception; declarations without valid preference excerpts fail input validation.
4. Subjective overall numeric score to one decimal, complete when every configured dimension is rated or clearly labeled “partial” when only some are rated. Use only rated dimensions in the numerator/denominator and contributions. Show all missing dimensions and reasons, rated/configured dimension counts, and rated/total configured importance. When none is rated, show no numeric aggregate or normalized contributions and list every missing dimension. Work arrangement is excluded from this calculation.
5. Separate decisive outcome and its matched declarations, their excerpts/types, reasons and evidence. Show unresolved declarations alongside confirmed matches, labeling any outcome based on confirmed matches only. With no supplied declarations, state “no exceptional preference applies.”

When opposing exception kinds match, print “conflicting exceptions,” show both sides, and leave the decision to the user. Never override this with weights or numeric scores. A supported exception outcome can be shown alongside a partial score or when no overall numeric score is available; it does not resolve those missing facts. Identify the report as five dimensions for this increment rather than four dimensions in total. Future dimension additions are outside this command version's supported profile keys.

Preserve the existing text renderer for legacy output and extend with a separate personalized renderer. Apply `safe()` to all user/model/source-derived terminal values. Exact prose, whitespace, and ordering within evidence lists are not a public machine-readable format; stable IDs and states are internal/evaluation contracts. No JSON output flag or product report persistence is added.

## Failures and exits

| Exit | Meaning | Output |
| --- | --- | --- |
| 0 | Successful assessment, including missing-evidence/unresolved-exception outcomes; existing help/auth successes | Report to stdout for assess |
| 2 | Invalid arguments, unreadable/invalid HTML or profile, unsupported profile version/names, invalid weight/declaration | Actionable local diagnostic on stderr; no success report or model request |
| 1 | Auth/provider/model/timeout failure, invalid model schema, wrong ID coverage, invalid evidence/preference references, absent/ambiguous target posting | Explanatory safe diagnostic on stderr; no success report |
| 130 | User interruption | Interrupted diagnostic; no success report |

A failure in the exception pass must not print the already obtained work/fit results as a successful report. Do not print source/profile data or raw provider validation bodies in errors. No retry or billing fallback. Existing per-request deadlines apply; two or three requests can consume up to 360 or 540 inference seconds respectively. Successful empty information is distinguished from unusable/ambiguous posting input.
