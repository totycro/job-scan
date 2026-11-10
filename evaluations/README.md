# Golden evaluation workflow

`cases/` holds reusable rich postings; `fixtures/` holds focused cases. `manifest.json`
contains one version-2 required list for `work_arrangement` and `personalized` entries.
Each typed entry selects a posting, nullable profile and expectations by stable pair ID.
Repeated postings can use distinct profiles. There is no manifest-path or mode-filter option.
`coverage.md` maps cases to requirements. Missing annotations mean not evaluated;
explicit null/not_stated means checked absence; omitted fields impose no assertion.
Unsupported expectation fields fail validation. Expected findings are never model-generated.

Run from the repository root. `--check` performs offline readiness checks without inference:

```bash
uv run --locked python evaluations/run.py --check --output .local/evaluations/readiness.json
uv run --locked python evaluations/run.py --live --recordings-dir tests/recordings/inference --output .local/evaluations/latest.json
```

Live calls use subscription allowance and the actual app transport. Pending/stale content or
criterion reviews never count as passes. Every required case must be covered. The runner
checks arrangement sets, quantity/period pairs, checked absences, schema and quote provenance;
it does not establish semantic entailment by quote existence or exact-prose comparisons.
The data-model document defines projection from response findings to golden fields.

Reports record Git/source/input/expectation/metadata/prompt/schema hashes, case/criterion keys,
model requested and returned, reasoning, timestamp, structured findings, terminal reports,
automatic outcomes and limitations. An immutable run ID binds manual review. `.local/` is
Git-ignored. No OAuth values or identity claims belong in evaluation reports.

## Manual review

Inspect each result and terminal report against source context, required findings and
prohibited conclusions. Review evidence relevance, role/location associations and report
usability. Author a JSON file with the report's exact run ID and a case entry for each result:

```json
{
  "run_id": "copy the run_id from latest.json",
  "reviewer": "Owner",
  "cases": {
    "cases/posting-01": {
      "semantic_findings": true,
      "evidence_relevance": true,
      "prohibited_conclusions_absent": true,
      "report_usable": true,
      "notes": "Reviewed against the supplied HTML and preferences."
    }
  }
}
```

Use `report_usable` for unsuccessful-posting cases to confirm the diagnostic explains the
failure. Include every required pair ID, including the preserved baseline posting-path IDs;
missing, duplicate or extra case coverage cannot establish acceptance.

```bash
uv run --locked python evaluations/run.py --review .local/evaluations/latest.json --manual-review .local/evaluations/manual-review.json --output .local/evaluations/reviewed.json
```

Review mode makes no inference calls. Changes to application/evaluation code, manifest,
lockfile, source HTML, profile bytes, expectations or source-review metadata invalidate the recorded review.
A new model/configuration requires a new run and review. Exit 1 means failed checks or
pending review; exit 0 means all mandatory checks and supplied reviews passed. Owner review
must be actually received; agents must never fabricate approvals.

## Recordings

`--recordings-dir` is developer tooling, not an application replay mode. It records only
inference HTTP requests as method/URL/body hash plus sanitized SSE event fields. It never
records OAuth/discovery/refresh requests, headers, callbacks, or tokens. Generic corpus HTML
contains fictional identities. Recording buffers the live SSE before replaying its contents
through the ordinary adapter, under the same total inference deadline. Review recordings
before versioning. Actual recordings are not expected-answer oracles; see `tests/recordings/`.

## Separate user and worker VMs

The user may authenticate in a browser on a different VM. The one-time helper encrypts only
the selected job-scan registration, including refresh credentials, for the worker's ephemeral
public key. Plain credentials and the private key never enter the shared workspace or chat.
The worker retains its own persistent host ID. Unrelated registrations are not exported.

Worker: `uv run --locked python evaluations/auth_transfer.py prepare`

Signed-in user's terminal: `uv run --locked python evaluations/auth_transfer.py export`

Worker: `uv run --locked python evaluations/auth_transfer.py import`

The shared directory is `.local/auth-transfer/`, ignored by Git. Private key and imported
credentials live in the receiving VM's owner-only job-scan config directory. Successful import
removes the shared envelope/public key and the ephemeral private key. Keep local job-scan
commands idle afterward so the VM owns later refreshes. This is a session transfer, not a
credential synchronization service; imported access can be revoked through normal sign-out.
The flow follows [OpenAI's VM transfer guidance](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms).


## Personalized corpus review and acceptance

The [personalized index](personalized/README.md) links every new fictional source/profile pair
and its manually specified semantic expectations. Their source and expectation review fields
remain `pending_owner_review` until the owner actually reviews them. Do not transplant the
historical baseline approval to changed inputs or to a new full-suite run. Review source text,
preference excerpts, expected states and prohibited conclusions before live capture.

Readiness checks all required coverage groups, strict profiles, original-byte hashes, exact
source/preference excerpts, declaration IDs and comparative pair references, without auth or
network access. All required cases must be ready before `--live` opens a session. Exit 1 is
expected for readiness; only a complete accepted run with its bound owner review exits 0.

Personalized reports retain five identified dimensions. Four have subjective scores, with
complete/partial weighted means over rated configured dimensions and explicit missing
coverage; if none is rated no numeric overall score exists. Work arrangement stays qualitative.
Optional exceptions use a separate pass and locally reduced decisive outcome; opposing types
never get a winner from weights. Facts come only from supplied HTML. Profiles transmit relevant
prose, never local paths/hashes or weights; only fictional profiles belong in this corpus.

The runner records original posting/profile/expectation/metadata hashes, manifest and code/lock
hashes, per-pass requested/returned model, low reasoning, timing, effective prompt/schema
version/hash, request-byte hash, structured result and failures. Model scores may vary even
for identical requests. Broad bands and relative direction are owner-reviewed semantic oracles,
not exact-score guarantees. Required/prohibited prose judgments and evidence entailment remain
owner checks, not substring-based claims of semantic correctness.

Each inference pass has a 180-second total deadline and a 10-second connect timeout; personalized
requests have a 360/540-second maximum inference budget excluding auth, with no retry. Review
the current immutable full-suite run after recordings and offline checks pass. Final acceptance
and convergence remain pending until actual source and result reviews have been received.


## Accepted feature-002 suite before the Python 3.15 upgrade

Run `b1d1383f7a6856baf98353aa9b9133bc0455ead4951eb5bf26d732eb31aa0486` contains 47 automatic passes and an
explicit owner-approved full-suite review (`accepted=true`). It used `gpt-6.1-sol` with low
reasoning throughout. All 298 socket-blocked tests pass at 98.04% coverage; 64 distinct
request cassettes support the current replay suite. The accepted artifact is
`.local/evaluations/reviewed.json`; `.local/evaluations/review.md` presents the original
results for inspection. This acceptance is bound to the original hashes and is not transferable
to future code, input, prompt/schema, lockfile or model-configuration changes.

The 2026-11-09 Python 3.15/dependency upgrade changed the lockfile, so this run's acceptance
is historical. The upgraded environment passes all 298 offline tests at 98.04% coverage
and corpus readiness for all 47 cases. No new live result review is claimed; see the
[upgrade validation](../specs/002-personalized-job-ratings/quickstart.md#python-315-and-dependency-upgrade-2026-11-09).
