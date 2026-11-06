# Golden evaluation workflow

`cases/` holds reusable rich postings; `fixtures/` holds focused cases. `manifest.json`
selects all mandatory case paths and the supported `work_arrangement` criterion.
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
failure. Include all remaining case paths; a missing review stays unsuccessful.

```bash
uv run --locked python evaluations/run.py --review .local/evaluations/latest.json --manual-review .local/evaluations/manual-review.json --output .local/evaluations/reviewed.json
```

Review mode makes no inference calls. Changes to application/evaluation code, manifest,
lockfile, source HTML, expectations or source-review metadata invalidate the recorded review.
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

Worker: `uv run python evaluations/auth_transfer.py prepare`

Signed-in user's terminal: `uv run python evaluations/auth_transfer.py export`

Worker: `uv run python evaluations/auth_transfer.py import`

The shared directory is `.local/auth-transfer/`, ignored by Git. Private key and imported
credentials live in the receiving VM's owner-only job-scan config directory. Successful import
removes the shared envelope/public key and the ephemeral private key. Keep local job-scan
commands idle afterward so the VM owns later refreshes. This is a session transfer, not a
credential synchronization service; imported access can be revoked through normal sign-out.
The flow follows [OpenAI's VM transfer guidance](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms).
