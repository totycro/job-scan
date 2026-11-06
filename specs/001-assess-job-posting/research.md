# Research: Assess a Job Posting

**Status**: Decisions proposed for plan review; Python, subscription-based ChatGPT access, and ty for type checking are owner constraints. Research resolves the technical choices; it does not establish account eligibility or model quality.

## 1. Python and development tools

**Decision:** Python 3.14, stdlib argparse, uv with a committed lockfile, Ruff, ty, pytest/pytest-cov. Library/tool versions will be resolved and locked during implementation rather than invented here.

**Rationale:** The owner prefers Python, and the reference project already uses 3.14. One file input and simple subcommands need no CLI framework. Locking keeps development/checks repeatable. Explicit lint rule families make the strict policy reviewable. Branch-aware combined coverage has a clear 90% gate.

**Alternatives:** TypeScript offers no clear advantage here; Typer/Click add dependencies for little immediate value. The reference uses ty; mypy strict was considered for its explicit strict configuration and mature validation-model integration. However prefer ty due to speed, iteration speed is essential. The owner selected ty; the plan defines explicit strict settings without changing product requirements.

Sources: [argparse](https://docs.python.org/3/library/argparse.html), [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/), [Ruff rules](https://docs.astral.sh/ruff/linter/#rule-selection), [ty configuration](https://docs.astral.sh/ty/reference/configuration/), [coverage calculation](https://coverage.readthedocs.io/en/latest/branch.html).

## 2. Subscription transport from the owner's reference

**Decision:** Adapt generic pieces from `../fyntok/src/fyntok/ai.py` and `auth.py`, inspected at sibling Git HEAD `8b2f08977ae259e06e00716afba596869e51af1c`. Preserve source attribution when adapting. Use HTTPX and PyJWT locally, with a separate job-scan registration/store and no runtime dependency on fyntok. Do not carry over finance prompts or tracing infrastructure.

**Rationale:** The reference already implements OAuth permission checking, token refresh, and completion-gated SSE handling. Official documentation describes using an authorized OAuth bearer token with the public Responses endpoint, `store=false`, and `stream=true`. Interrupted streams must not be accepted as successful. This supports the requested subscription path without an API-key billing fallback.

**Model:** Begin with the reference's `gpt-6.1-sol` and explicit `low` reasoning. Use only an account-available model; expose an optional model choice, preserve actual settings in evaluations, and fail clearly on unsupported capabilities. Neither local code inspection nor general documentation proves this particular account can use the selected model.

**Alternatives:** A paid API key conflicts with the owner's constraint. Importing all of fyntok couples unrelated applications. An OpenAI SDK can carry OAuth tokens, but offers less reuse of this existing stream/error boundary. Browser automation and private ChatGPT backend endpoints are unnecessary.

Sources: [official subscription inference contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [model capabilities](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [error recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery). The actual adapter/reference is local source evidence, not proof of deployed account behavior.

## 3. Authentication lifecycle

**Decision:** Adapt the reference's registration, PKCE/state/nonce validation, verified identity, per-registration token records, atomic protected storage, refresh, and sign-out. Support CLI login/status/account selection/logout. Keep credentials outside the repository under the job-scan configuration directory; retain issued registration IDs when reauthorizing. Do not use fyntok's credentials or share its app identity.

**Rationale:** Identity-only sign-in does not authorize plan usage. Missing permission or a usage-limit failure must stop inference. Reusing working generic source keeps this necessary provider integration bounded. Sign-in is an implementation dependency of the selected provider, not website authentication or a new assessment-management feature.

**Alternatives:** Pasting bearer tokens into CLI arguments exposes them and omits refresh/revocation behavior. A single overwritten credential record loses registration identity on reauthorization. Full account/profile UI is unnecessary; simple CLI selection suffices.

Sources: [registration/sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [sessions and protected storage](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions).

## 4. Preserve raw HTML and validate evidence

**Decision:** Send the exact decoded HTML inside the request payload. Preserve source bytes/hash; return exact HTML excerpts with occurrence indexes and generate offsets locally. No HTML parser or text extraction dependency initially. Validate the response with strict Pydantic models, forbidden extra fields, and evidence checks before deterministic fit mapping.

**Rationale:** Pass-through preserves headings, table relationships, attributes, and order without building a normalization pipeline. Exact excerpts make provenance verifiable even for minified HTML. Model interpretation of those relationships still needs golden evaluation; quote presence alone does not establish entailment. File size/deadline limits prevent silent truncation or indefinite runs.

**Alternatives:** BeautifulSoup with an explicit parser could provide element locators later, but adds tree normalization and parser-dependent malformed-HTML behavior. Text-only extraction loses potentially relevant structure. Browser rendering exceeds the agreed scope. A model cannot repair a loading-only snapshot.

Sources: [Pydantic strict validation](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/), [BeautifulSoup parser differences](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#differences-between-parsers). Raw pass-through and evidence handling are design judgments, not library guarantees.

## 5. Recorded system tests and live evaluation

**Decision:** Replay reviewed HTTP response fixtures through HTTPX transport injection in real-component CLI tests. Block unrecorded sockets with pytest-socket. Record sanitized inference SSE; use synthetic authentication responses where recording would expose credentials. Run actual subscription calls only in an explicit live evaluation.

**Rationale:** This keeps stream handling and application logic real while replacing only external calls. HTTPX supports transport injection. Matching request bodies prevents unrelated prompt/model/input changes from silently reusing an old response. Keep replay infrastructure small and test-only. Human-authored expectations, rather than recordings or a judge model, define correctness.

**Alternatives:** VCR.py/pytest-recording is useful for general HTTP capture but unnecessary for one transport boundary with a small fixture set. Mocking the whole AI adapter bypasses important integration behavior. Always-live tests are variable and consume subscription allowance. A parent-process interceptor does not automatically cover child subprocesses, so system tests invoke `main(argv)` in-process and use a separate entry-point smoke test.

Sources: [HTTPX custom/mock transports](https://www.python-httpx.org/advanced/transports/), [pytest-socket](https://github.com/miketheman/pytest-socket).

## Remaining validation dependencies

Three [rich generic postings](../../evaluations/cases/README.md) now retain substantive source content and owner-authored short notes. Use one shared corpus across features, adding independently reviewed criterion keys to each case's expectations; absent keys mean not annotated. Content and detailed expectations remain pending owner review, bound to posting hashes. Small synthetic edge-case fixtures are separate; roughly ten shared cases is a working goal, not a mandatory count. The supplied remote example was an outer page with a job-board iframe; a direct download of the embedded document recovered the actual posting. Preserve this capture distinction for future retrieval design without adding fetching to the current feature.

The original on-site page is 2,144,770 bytes and exceeds the proposed 256 KiB input limit. The generic copies omit executable/scaffolding data while retaining substantive content, so their smaller sizes are not evidence that the limit handles complete original pages. Review that limit with the owner before plan adoption. The structure-sensitive pair and other uncovered scenarios still need manually authored expectations. Live account eligibility, inference quality, and recorded stream compatibility have not been tested.
