# URL input validation

Validation date: 2026-11-10. Product authority:
`docs/plans/2026-11-10-0808-feat-job-posting-url-input-plan.md`.

## Implementation and deterministic checks

The positional assessment input accepts an HTTP(S) URL or a saved HTML path. URL input uses
Playwright 1.65.0 and its Chromium 158 build, with a fresh context and a public-destination
TCP proxy. The proxy resolves once, checks every returned IP, and connects to a numeric
validated IP; browser DNS rebinding cannot change that connection. Chromium's loopback proxy
bypass and non-proxied WebRTC UDP are disabled. No account browser state is imported.

Acquisition preserves explicit and computed hidden markers, keeping inactive alternatives
distinguishable from the visible target. Empty visible network-loaded frames and failed
fetch/XHR requests stop acquisition, including failures after a readable shell loads.
There are no site-specific exceptions. Failed incidental data requests, including anonymous
identity requests, also conservatively fail because completeness cannot be verified.

Acquisition keeps submitted query parameters/fragments, waits at least five seconds and two
seconds of unchanged document snapshots, reads the main page and visible frames (including
cross-origin frames), expands open shadow roots, and retains structured data from the head.
Scripts/styles, SVG drawing paths and nonsemantic attributes are removed; SVG text and
accessible labels remain evidence. All remaining content is
assembled without truncation, with contributing URLs and a SHA-256 hash. The limits are 60
seconds, 24 documents, and 256 KiB of assembled UTF-8. Unknown or blocked frame content fails
rather than allowing an assessment of only the readable main-page shell.

Reports identify submitted, final and frame URLs. Quotes and locations resolve against the
exact acquired document shared by all passes. URL-specific inference instructions identify the
selected job and reject expired, ambiguous, blocked, login-only, incomplete or absent postings.
The saved-file prompt and existing provider request bytes remain unchanged. Arrangement
uncertainty and personalized ratings/exception behavior remain the existing criterion policy.

Automated coverage includes:

- Real Chromium with all HTTP routed to authored fixtures: query/fragment-selected JavaScript,
  delayed cross-origin frames, oversized scripts, open shadow DOM, head structured data,
  blocked HTTP, failed description requests, empty frames and hidden alternative job claims.
- Authored synthetic semantic and structured posting pages, replayed through Chromium
  and checked for invented job titles and substantive sections. Real downloaded pages
  and their identifying metadata are kept only under ignored `.local/` storage.
- Real local TCP proxy exercises HTTP and CONNECT forwarding, address pinning and rejection of
  private IPv4/IPv6 destinations. An actual Chromium request to a listening loopback origin
  is blocked without contacting it. Browser WebSocket routing is not separately tested.
- URL qualitative CLI replay using a real provider response originally recorded for the same
  posting HTML, with updated acquisition/provenance context. This is explicitly an adapted
  replay, not a claim of a new live URL assessment recording.
- URL personalized CLI replay through work arrangement, fit and exceptions, with the same
  evidence content in every pass. Existing file-based actual-provider recordings still pass.
- Invalid arguments and profiles fail before browser/authentication/inference. Retrieval limits
  and errors include the saved-HTML fallback. Provider failure paths never emit reports.

Before the repository-content cleanup, verification passed 346 tests with 97.27% combined
statement/branch coverage, plus Ruff lint/format and strict ty. Those results predate removal
of captured-page replay and site-specific exceptions; current cleanup verification is recorded below.

After cleanup: **347 tests passed** with **97.12%** combined statement/branch coverage
in 72.69 seconds. Ruff lint/format and strict ty passed. A local smoke check exercised
the evaluation script with a URL file containing blank lines, one successful retrieval and
one failure; numbered captures and result metadata were correct without live requests.
The moved captures and real URL input file were confirmed ignored by Git. Existing
anonymized evaluation fixtures were left unchanged. Live compatibility was not rechecked.

Independent full code review identified failed description requests, empty description frames,
and lost visibility context. All three findings were fixed with red-before-fix Chromium tests.
Independent bounded followup verified all five relevant cases and found no unresolved concrete
defect in those fixes. The code-review receipt and followup are local artifacts under
`/tmp/compound-engineering-1000/ce-code-review/20261110-url-review/`; they are not release artifacts.
The separate simplification pass found one redundant comment, removed without behavior changes.

Required commands (locked uv environment only):

```bash
uv run --locked ruff check src tests evaluations
uv run --locked ruff format --check src tests evaluations
uv run --locked ty check src tests evaluations
uv run --locked python -m pytest --strict-markers --disable-socket --cov=job_scan --cov-branch --cov-fail-under=90
```

The suite enables sockets only for explicitly marked browser/local-proxy tests. Browser tests
route or abort every HTTP request; proxy tests use local origins or reject private destinations.
Live acquisition is separate and explicitly requested through:

```bash
uv run --locked python -m evaluations.url_input --urls-file .local/evaluations/url-input-source/urls.txt --output .local/evaluations/url-input
```

## Live example observations

Before the cleanup, the production retriever was used for five locally supplied links.
Four postings were retrieved and manually inspected for the selected job and substantive
content. One returned HTTP 403 with an automated-access challenge, although a separate
reader could view the posting. A later browser diagnostic remained blocked. These are
historical observations, not verification of the stricter retriever after removal of
site-specific exceptions; current live compatibility has not been reverified.

Source URLs, job details, captures and the original manifest are kept in ignored local storage
under `.local/evaluations/url-input-source/`. The evaluation script reads one URL per line
from a local UTF-8 file and writes numbered outputs. Repository tests use invented examples.
A blocked or failed example remains an acceptance gap, not successful coverage.

Live inference was attempted with the configured default `gpt-6.1-sol`, low reasoning.
The saved ChatGPT session returned “Session expired or revoked. Sign in again.” before any
assessment. No live URL assessment result or new golden-model evaluation is claimed. Refreshing
sign-in and rerunning example assessments is necessary to establish live semantic acceptance.
Because URL-specific availability/selection instructions are new, deterministic replay alone
cannot establish their model accuracy; the existing unchanged file prompts retain their golden
regression coverage.

## Constitution and convergence

- Simplicity: one browser acquisition path and one existing assessment pipeline; no crawler,
  site allowlist, new criterion, saved-report subsystem or alternate billing/provider route.
- Evidence: immutable assembled document and per-document URLs; no truncation and no inferred
  missing facts. Retrieval and job-identification failures do not produce successful reports.
- Criteria: acquisition is separate from work arrangement, dimensions and exception policy.
- Development: exact dependency pin plus uv lock; strict Ruff and ty retained, with the existing
  90% coverage target and full suite required. Browser and inference external boundaries use
  recorded or authored responses in tests; only the explicit probe and assessment attempt were live.
- CLI: both input forms use the same command. Existing saved-file input remains available.
- Golden cases: unchanged file-provider recordings remain the assessment regression guardrail.

Convergence against the implementation units and acceptance examples:

| Contract area | Evidence | Remaining gap |
| --- | --- | --- |
| URL/file dispatch and profile preservation | CLI/replay tests | None in deterministic behavior |
| JavaScript, frames, shadow content and exact quotes | Chromium and evidence-resolution tests | Arbitrarily delayed or continuously changing pages may exceed the finite retrieval budget |
| Query/fragment identity and ambiguity gate | Browser selection tests; explicit target URL in inference input | Live model validation blocked by expired session |
| Complete bounded input and retrieval failures | Limit/error tests and blocked-frame tests | Oversized pages fail explicitly; no automatic site-specific extraction |
| Provenance across redirects/frames | Source assembly/report tests and historical local frame inspection | None in deterministic behavior |
| Five-site acceptance | Historical local review: four postings inspected, one HTTP 403; stricter retrieval not reverified | Five-site success requirement is not yet met |
| Unknown job facts versus absent posting | Existing provider recordings, unchanged criterion policy | New URL-specific expiry/block detection awaits live model evaluation |

The implementation is locally verifiable, but full feature acceptance remains incomplete until
the local examples pass with the stricter retriever and URL-specific instructions are evaluated with a valid session.
Do not treat passing automated checks as completion of those outstanding live requirements.
