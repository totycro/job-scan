---
title: Job Posting URL Input - Plan
type: feat
date: 2026-11-10
topic: job-posting-url-input
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
---

# Job Posting URL Input - Plan

## Goal Capsule

- **Objective:** Assess a specific job posting directly from its link without manually downloading HTML.
- **Product authority:** The user-approved scope in this Product Contract governs this feature.
- **Open blockers:** None; technical retrieval choices remain for planning.

---

## Product Contract

### Summary

Add URL input to the existing assessment flow, including automatic retrieval of JavaScript-rendered postings and postings embedded in frames.
Preserve saved-HTML input and the current work-arrangement and personalized assessments.

### Key Decisions

- **Automatic retrieval.** Governs R2, R8. (session-settled: user-directed — chosen over assisted browsing: the user selected fully automatic retrieval with clear failures and saved HTML as fallback.)
- **Extend input acquisition.** Governs R1, R5. Keep the existing assessment capabilities rather than introducing new assessment criteria.
- **General URL support with concrete examples.** Governs R3, R10. The supplied sites are acceptance coverage rather than a domain allowlist.

### Requirements

**Input and retrieval**

- R1. Accept one public HTTP(S) job-posting URL as input to the existing CLI assessment flow while retaining local saved-HTML input.
- R2. Retrieve the posting automatically, including content that requires JavaScript execution or lives in relevant frames, including frames on another origin.
- R3. Identify the specific job selected by the supplied URL, preserving job-selecting query parameters and fragments through retrieval as needed.
- R4. Retrieve the substantive posting content without silently omitting material needed for assessment because of page boilerplate, rendering, frame boundaries, or input limits.

**Assessment and evidence**

- R5. Apply the existing work-arrangement assessment and optional profile-based ratings to the retrieved posting.
- R6. Ground factual findings and supporting quotations in the exact retrieved content supplied for assessment, including any content acquired from frames.
- R7. Report the submitted source URL and identify a different final page or frame URL when that supplied the assessed posting.

**Failure behavior**

- R8. Complete retrieval without user interaction, or terminate with a clear explanation and a suggestion to use the saved-HTML input path.
- R9. Fail without a successful assessment when the target posting is blocked, expired, ambiguous, unreadable, or cannot be retrieved sufficiently for assessment.

**Coverage**

- R10. Support all five supplied examples while their postings are publicly available; successful coverage requires the correct job and substantive posting content, not merely a successful HTTP response.
- R11. Continue to express uncertainty for missing or conflicting job facts in an otherwise identifiable posting, consistent with the existing assessment behavior.

### Acceptance Examples

- AE1. **Covers R1, R3, R5, R10.** Each URL in the table below yields an assessment of its selected job, with profile-based ratings when a profile is supplied.
- AE2. **Covers R2, R4, R6, R7.** When the posting appears only after JavaScript execution or inside a frame, its substantive content is retrieved and supporting evidence resolves against the content actually analyzed.
- AE3. **Covers R3, R9.** When a link selects one job on a page containing several vacancies, assess only the selected job; fail if that job cannot be identified unambiguously.
- AE4. **Covers R4, R9.** A large page containing substantial navigation or scripts is handled without silently truncating the posting; inability to obtain sufficient content produces an explanatory failure.
- AE5. **Covers R8, R9.** A retrieval block, required login, unresolved consent obstacle, timeout, or unavailable posting ends without an assessment and explains the saved-HTML fallback.
- AE6. **Covers R1, R5, R6.** Existing saved-HTML assessments continue to work, including optional provenance URLs and preference profiles.
- AE7. **Covers R9, R11.** A readable posting that omits a work-arrangement detail produces uncertainty; a careers homepage without the selected posting produces a failure.

Real acceptance URLs are kept in an ignored local input file, such as
`.local/evaluations/url-input-source/urls.txt`. They are not part of this document.
Tracked fixtures use invented postings and reserved example domains to cover direct pages,
query-selected jobs, fragment-selected jobs, cross-origin frames and blocked requests.

### Scope Boundaries

Website login, manual browser assistance, CAPTCHA solving, job discovery, batch processing, company research, new assessment criteria, and saved-report management are excluded.
Retrieval is limited to the selected posting and the content needed to obtain it, rather than general crawling.
Browser libraries, site-specific fallbacks, and extraction mechanisms are technical planning decisions.

### Dependencies / Assumptions

Public job pages can change, expire, or behave differently across retrieval environments.
If an example is unavailable during verification, record that limitation explicitly; an explanatory failure does not establish successful coverage under R10.
Use authored synthetic examples to retain regression coverage of rendering, frames, and job selection independently of live availability. Keep downloaded content in ignored local storage.

### Outstanding Questions

**Deferred to Planning**

- Select the retrieval mechanism and determine whether a simple request, browser rendering, embedded structured posting data, or a combination best meets R2-R4 and R10.
- Define evidence representation and source attribution across main-page and frame content under R6-R7.
- Define finite retrieval deadlines, resource limits, browser installation requirements, and handling of oversized pages under R4 and R8-R9.
- Define the CLI syntax for URL input and its interaction with the existing provenance-only source URL option under R1.
- Define recorded and live verification of the supplied examples, including expected job identity and substantive sections under R10.

### Sources / Research

- `src/job_scan/cli.py:23`: current 256 KiB saved-input cap; `src/job_scan/cli.py:30`: saved-HTML loading and provenance-only URL handling.
- `src/job_scan/cli.py:95`: work arrangement, personalized fit, and optional exception passes use the same loaded HTML.
- `src/job_scan/evidence.py:13`: quotes and occurrence numbers are matched against loaded HTML; character positions and line numbers are computed from that content.
- `specs/001-assess-job-posting/spec.md:81`: URL fetching and browser rendering were previously excluded; this feature expands that boundary.
- Initial direct HTTP probes encountered pages exceeding the current cap and an HTTP 403 response while a separate reader could access the posting. These observations motivate R2 and R4, but do not establish rendered-browser compatibility.

---

## Planning Contract

Product Contract unchanged. This enrichment resolves its technical questions; the original
outstanding questions above remain as provenance for the planning handoff.

### Key Technical Decisions

- **KTD1. Browser acquisition.** Use exactly pinned Playwright with Chromium, installed
  explicitly through the locked uv environment. Rendering and cross-origin frame access
  use the same browser, without a separate HTTP fallback that could return a different job.
  Preserve the complete submitted URL, including query and fragment. Fresh browser contexts
  have no account cookies. No interactive consent, login, CAPTCHA solving, or crawling.
- **KTD2. Evidence document.** Serialize rendered document bodies from the main page and
  visible frames, preserving visibility markers and removing executable scripts, styles, and non-content browser resources, retaining
  structured JobPosting data. Include submitted and per-document URLs in the assembled
  assessment HTML. Do not clip text or select a posting by an arbitrary first-match heuristic.
  URL-specific instructions at the existing identified/absent/ambiguous assessment gate evaluate the selected job,
  treating related jobs as context only. Evidence positions refer to this exact assembled
  document. Reports identify submitted, final, and contributing frame URLs.
- **KTD3. Limits and failures.** Allow 60 seconds total for acquisition, including browser
  startup, navigation and rendering. Observe a stable rendered snapshot after document load,
  with a minimum rendering grace period for delayed frames. Bound assembled UTF-8 HTML at
  256 KiB and frame count at 24; exceed either by failing without inference or truncation.
  Browser network connections use a public-address TCP proxy that connects directly to the validated
  numeric IP, including redirects and WebSocket tunnels. Disable browser loopback proxy bypass
  and non-proxied WebRTC UDP. Missing browser, navigation errors, blocked responses, unreadable documents and incomplete
  frame acquisition, empty visible network frames, and failed posting data requests fail clearly, with the saved-HTML command as fallback. A page that loads
  but lacks the selected posting fails at the existing assessment gate, also with fallback.
- **KTD4. CLI compatibility.** The positional argument accepts a file path or an HTTP(S) URL.
  `--source-url` stays provenance-only for files and is rejected with URL input. Validate
  profile and URL arguments before browser or inference work. Saved files retain their byte
  hashing, limits and evidence semantics. Retrieved sources use the assembled document hash
  and have no fictitious filesystem path.

### Sources and risks

Playwright supports [frame access](https://playwright.dev/python/docs/frames) and requires
[matching browser binaries](https://playwright.dev/python/docs/browsers). Dynamic sites can
remain blocked or expire; live failures must be recorded honestly and do not prove R10.
Browser availability under Python 3.15 is an installation prerequisite to verify in execution.
The existing work-arrangement prompt and status gate provide job identification; acquisition
must provide the selected URL as explicit context without granting page text instruction authority.

## Implementation Units

### U1. Acquire rendered posting evidence

**Goal:** Obtain bounded, complete rendered main/frame content automatically.
**Requirements:** R2–R4, R6–R9; AE2–AE5.
**Dependencies:** None.
**Files:** `src/job_scan/retrieval.py`, `src/job_scan/models.py`, `pyproject.toml`, `uv.lock`,
`tests/unit/test_retrieval.py`, `tests/system/test_url_retrieval.py`.
**Approach:** Keep browser I/O in acquisition and pure document assembly separately testable.
Use a finite total deadline and reject incomplete/oversized results. Capture contributing URLs.
**Patterns to follow:** Strict Pydantic source models and fail-before-report behavior.
**Execution note:** Establish failing document assembly and real-browser fixture tests first.
**Test scenarios:**

- Preserve query and fragment through JavaScript job selection.
- Acquire delayed cross-origin frames and resolve quotes in the assembled document.
- Remove oversized scripts without losing substantive body or structured posting data.
- Fail on oversized substantive content, blocked HTTP, empty documents, timeouts and frame errors.

**Verification:** Deterministic routed Chromium pages exercise actual rendering and frame access;
unit tests cover limits and failures. Routed pages are authored fixtures, not live captures.

### U2. Integrate URL assessment and provenance

**Goal:** Assess links using existing qualitative and optional personalized passes.
**Requirements:** R1, R3, R5–R9, R11; AE1, AE3, AE6, AE7.
**Dependencies:** U1.
**Files:** `src/job_scan/cli.py`, `src/job_scan/report.py`, `tests/unit/test_cli.py`,
`tests/system/test_url_retrieval.py`.
**Approach:** Dispatch file/URL input once, share the acquired source across passes and retain
existing source validation. Render retrieved provenance and wrap URL-specific assessment
failures with the saved-HTML fallback without changing file error behavior.
**Patterns to follow:** Existing CLI and recorded-provider system tests.
**Test scenarios:**

- File input and provenance-only option retain existing behavior.
- URL input reaches the existing assessment flow, with the exact retrieved document.
- Invalid URLs/options/profiles fail before acquisition or authentication.
- Absent/ambiguous postings never produce reports; missing arrangement facts remain uncertain.

**Verification:** Unit/CLI tests and existing recorded inference replay pass; browser and
provider boundaries are substituted independently, with real internal assembly and evidence logic.

### U3. Verify examples and document operation

**Goal:** Provide reproducible setup, live-example observations and convergence evidence.
**Requirements:** R10 and all acceptance examples.
**Dependencies:** U2.
**Files:** `README.md`, `evaluations/url_input.py`, `specs/003-job-posting-url-input/validation.md`,
`tests/system/test_url_retrieval.py`.
**Approach:** Probe all five links with the production retriever; record job identity,
substantive sections, source URLs and failures. Keep live captures and identifying details in ignored local storage; author synthetic fixtures for replay.
Keep external provider recordings as the assessment regression boundary; no new criteria.
**Test scenarios:**

- Live probes record a separate result per example and never count retrieval failures as coverage.
- Authored synthetic pages retain invented job identity and substantive sections in deterministic replay.

**Verification:** Run all strict lint/type checks and the complete suite with at least 90%
combined statement/branch coverage. Record live limitations and remaining convergence gaps.

## Verification Contract

Use only `uv run --locked` and exact dependency pins. Required checks are Ruff lint and format,
strict ty on `src tests evaluations`, and pytest with sockets disabled and 90% combined
statement/branch coverage. Browser tests enable local transport only as needed, route all
browser HTTP through authored synthetic fixtures, and abort unmatched requests. Existing
provider SSE recordings remain the inference regression oracle. Live acquisition is a separate
explicit evaluation of the five links and must record actual availability and job identity.
No unrelated full personalized LLM evaluation is required because assessment criteria are unchanged.

## Definition of Done

All implementation units verified, required checks passing, CLI setup documented, live example
results recorded, and convergence assessed against every requirement. Any unavailable example
or unverified live inference remains an explicit limitation; do not call R10 satisfied without
correct-job/substantive-content evidence for every available example. Remove abandoned code.
