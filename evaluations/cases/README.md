# Shared posting corpus

Keep one reusable collection of rich, generic job postings. Start with these three and grow toward roughly ten representative cases as useful variations appear; ten is a working goal, not a feature-completion requirement. Add expectations for each criterion as features introduce it, using the same posting instead of making feature-specific copies.

The current files have been rebuilt from the originals. Source-content review remains **pending owner review**. On 2026-11-06 the owner approved all three work-arrangement expectations. All three retain that approval with matching posting hashes. Posting-03 is unchanged at 62,393 bytes, already within the proposed 256 KiB limit.

| Case | Owner's classification | Other retained material |
| --- | --- | --- |
| [posting-01](posting-01/posting.html) | Hybrid; days unspecified | German integration role, SAP technologies, responsibilities, qualifications, salary/hours, benefits, company background and JobPosting metadata |
| [posting-02](posting-02/posting.html) | Fully remote | Backend role, stack/skills, responsibilities, company context, benefits, Europe/UK eligibility, time zone and office-week invitations |
| [posting-03](posting-03/posting.html) | Onsite only | Engineering role, technical skills, experience requirements, related jobs, company background, JobPosting metadata and company-level benefits |

## Files and ownership

```text
posting-01/
  posting.html     # Shared source for current and future criteria
  metadata.json    # Provenance, capture method, transformations, content review and hash
  owner-note.txt   # Owner's original note, unchanged
  expected.json    # Expectations grouped by criterion, with separate review status
```

Source originals remain in the sibling `job-scan-examples` directory outside Git. Original URLs and real-to-fictional identity mappings are not part of this corpus. `metadata.json` refers to source filenames so the owner can compare locally. Case 02 uses `posting-02-embedded.html`, the actual iframe document, rather than the outer careers-page shell. Capture methods for cases 01 and 03 were not supplied and are recorded as unknown.

## Content preservation

Retain responsibilities, qualifications, technology names, pay, hours, benefits, company/industry descriptions, and relevant location/eligibility details. Preserve headings, paragraphs, lists, emphasis, definition-list/table associations, related-job boundaries, and source JobPosting metadata.

Employer/person/contact identifiers and link targets are fictionalized consistently. Broad geographic names, geographic restrictions, skill names and numerical quantities remain meaningful; they are not automatically sensitive identifiers. Precise coordinates in case 01 are rounded. These are generic test postings, not claims about the fictional employers in the real world.

Executable scripts, trackers, stylesheets/media and application forms are omitted. The job-description prose has not been replaced by filler. Relevant company-benefit descriptions recovered from embedded configuration are retained in an inert JSON block explicitly scoped to company-level information; they must not override a role-specific on-site label. The copies are not byte-identical archives or pixel-identical pages. Future browser/retrieval tests may need separate capture fixtures.

## Expectations by criterion

`expected.json` has `schema_version`, `case_id` and a `criteria` object. The initial key is `work_arrangement`. Future features add keys for their criteria without duplicating `posting.html` or inventing expected answers for unsupported criteria.

Each criterion records:

- `review_status`: `pending_owner_review` or `approved`.
- `expectation_authorship`: who supplied the note and drafted/reviewed the detailed expectations.
- `posting_sha256`: the exact HTML revision these expectations were reviewed against.
- `owner_note`: original owner guidance for this criterion, when supplied.
- `expected`: semantic field values to check, rather than exact report prose.
- `required_findings`, `evidence` (exact source quotes and zero-based occurrences), and `prohibited_conclusions`.
- `review_question`: an unresolved interpretation to settle before approval, when needed.

The current owner classifications are human-authored. The expanded checks were agent-drafted and owner-approved on 2026-11-06, subject to the per-case HTML revision and review status described above. Reading or generating a model response must never automatically approve or overwrite expectations.

**Absence has two different meanings:** an absent criterion key means this case has not been annotated for that criterion. An explicit expected value such as `home_working_schedule.status = "not_stated"` means the criterion was annotated and the posting is expected to omit that information. Omitted expected fields are not checks; explicit `null` values are checked absences.

## Review and change workflow

1. Add or change a generic posting while preserving useful content and structure. Record provenance and transformations in its metadata; never commit the private original.
2. Compare substantive details with the original. Mark content review in `metadata.json` as approved only after owner review confirms the transformed case still means what it should.
3. Author or review the expectations for each relevant criterion. Approve each criterion independently, record that review in `expectation_authorship`, and remove answered `review_question` entries.
4. Record the SHA-256 of the exact `posting.html` bytes in metadata and each reviewed criterion. Any later HTML edit makes old hashes stale: return affected reviews to pending, inspect all existing criteria, and approve against the new content. Do not merely refresh hashes to bypass review.
5. Commit the posting, metadata and reviewed expectations together. Git supplies corpus history; no database or separate dataset service is needed.

A feature's evaluation selects the criteria it supports. Missing criterion annotations are reported as **not evaluated/not covered**, never as passing or as missing source facts. Pending/stale expectations and pending content reviews cannot establish acceptance. Required feature coverage must be present and approved before feature completion. Unrelated future criterion keys are outside the current run.

Record the Git revision, selected case/criterion keys, input and expectation hashes, model/configuration, prompt/schema versions, results and limitations with each evaluation. Review evidence relevance as well as quote existence. A model change reruns evaluation; it does not rewrite the expected findings. If a future criterion needs external evidence, add feature-defined source fixtures alongside the posting rather than inventing facts from outside it.

## Focused fixtures and remaining work

Keep a few small, purpose-built edge-case fixtures separate from this shared corpus when implementation needs them. For example, the paired structure-sensitive test may change only which role a schedule belongs to while retaining the same words. Do not shrink the reusable postings to make those focused tests.

The three cases do not cover the entire first specification: explicit hybrid allowances/expectations, conflicts, missing arrangements, unusable input and the structure-sensitive pair still need reviewed expectations. Broader criteria remain unannotated. No assessment model has evaluated this corpus yet.

Original sizes are recorded in each metadata file. The original on-site capture is 2,144,770 bytes and exceeds the draft 256 KiB input limit. Removing website scaffolding from a test fixture is not a production solution to that limit; review it before adopting the technical plan.

Next: review transformed posting content, then resolve remaining plan decisions before `$speckit-tasks`. All three cases already have approved criterion expectations.
