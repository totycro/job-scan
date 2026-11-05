# Feature Specification: Assess a Job Posting

**Feature Branch**: `main` (no branch-creation hook configured)

**Feature Directory**: `specs/001-assess-job-posting`

**Created**: 2026-11-05

**Status**: Draft — awaiting owner review

**Input**: Build the first job-scan CLI workflow: accept one job-posting URL, evaluate the posting against the user's job criteria, and produce a readable assessment. Explain findings using source evidence and explicitly identify missing information. Use manually authored examples to define expected behavior. Defer external company research, commute estimates, and managing saved assessments to later features. Ask about actual criteria rather than inventing them. Stop after drafting and validating the specification for review.

**Owner-supplied criteria**: “whether the job offers remote work (best case), or hybrid work (also fine). if hybrid, check if it says how many days of work from home are allowed/expected”

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand the work arrangement (Priority: P1)

As a job seeker, I submit a posting URL and see its work arrangement and how that relates to my preferences: remote is preferred and hybrid is acceptable.

**Why this priority**: Work arrangement is the first criterion the owner has supplied. An evidence-supported assessment of it makes this increment useful.

**Independent Test**: Submit a posting represented by a manually authored case and compare its reported arrangement, evidence, and fit judgment with the expected findings.

**Acceptance Scenarios**:

1. **Given** a posting explicitly offering fully remote work, **When** assessed, **Then** the report identifies remote work, cites a supporting passage, and separately states that it matches the preferred arrangement.
2. **Given** a posting explicitly offering hybrid work, **When** assessed, **Then** the report identifies hybrid work with evidence and separately states that hybrid is acceptable.
3. **Given** a posting explicitly requiring full-time on-site work, **When** assessed, **Then** the report identifies on-site work and says it does not offer the stated remote/hybrid preferences, without inventing a hard exclusion or application decision.
4. **Given** a posting saying only that work is “flexible,” **When** assessed, **Then** the report identifies the arrangement as unclear rather than confidently calling it remote or hybrid.
5. **Given** remote work restricted by location, eligibility, or employer approval, **When** assessed, **Then** the report preserves those conditions without assuming the user's eligibility.
6. **Given** multiple work options or conflicting statements, **When** assessed, **Then** the report shows the alternatives or conflict and supporting passages rather than silently selecting one arrangement.

### User Story 2 - Understand hybrid home-working days (Priority: P1)

As a job seeker considering a hybrid role, I can see whether the posting specifies how many work-from-home days are allowed or expected.

**Why this priority**: Hybrid availability alone does not answer the owner's question about days at home.

**Independent Test**: Assess manually authored hybrid cases containing an allowance, an expected schedule, office-days-only wording, and an unspecified schedule; check that the distinctions survive in the report.

**Acceptance Scenarios**:

1. **Given** “up to two days working from home per week,” **When** assessed, **Then** the report preserves the upper limit and weekly period as an allowance, without treating it as a required or guaranteed schedule.
2. **Given** a stated expected home-working schedule, **When** assessed, **Then** the report identifies the number, period, and expectation with evidence.
3. **Given** hybrid work without a stated number of home-working days, **When** assessed, **Then** the report explicitly says the number is not stated.
4. **Given** only office-attendance days, **When** assessed, **Then** the report cites those days and identifies home-working days as unstated; it does not assume a five-day workweek to calculate them.
5. **Given** conflicting or conditional home-working schedules, **When** assessed, **Then** the report presents the statements and conditions and identifies uncertainty rather than inventing one definitive schedule.

### User Story 3 - Recognize an unsuccessful assessment (Priority: P1)

As a job seeker, I get an explanation when the input or available content cannot support an assessment, so I do not mistake failure for a negative fit judgment.

**Why this priority**: An inaccessible page is not evidence that a job lacks remote work.

**Independent Test**: Exercise invalid input, unavailable or unidentifiable postings, and failed assessments; verify that each has an explanatory failure instead of fabricated findings.

**Acceptance Scenarios**:

1. **Given** missing input, multiple URLs, or an unsupported URL, **When** the CLI runs, **Then** it explains that exactly one HTTP or HTTPS job-posting URL is required and produces no fit assessment.
2. **Given** an inaccessible, removed, sign-in-gated, or non-posting page, **When** submitted, **Then** the CLI explains the observed problem and reports an unsuccessful assessment without guessing inaccessible content.
3. **Given** a readable posting omitting work-arrangement information, **When** assessed, **Then** the report identifies missing information rather than a retrieval failure or an on-site arrangement.
4. **Given** an assessment process that fails or cannot produce source-supported findings, **When** results are reported, **Then** the CLI reports failure rather than presenting unsupported findings as a completed assessment.

### Edge Cases

- A remote-labelled title conflicts with mandatory office attendance: show both passages and the conflict.
- Remote work varies by country, probation period, or approval: preserve those conditions and unknown eligibility.
- Occasional home working is offered without a defined arrangement: report the actual wording and uncertainty.
- Home-working days use ranges, monthly allocations, maximums, or minimums: preserve their original period and qualifications.
- A page lists several jobs without an identifiable target: explain that the target posting could not be identified.
- Partially readable posting: report supported findings and missing information; fail if no posting can be identified.

## Requirements *(mandatory)*

### Functional Requirements

The scope and criteria listed under “Agreed Requirements” below come from the owner and constitution. The detailed behaviors and acceptance targets in this draft are proposed for review until adopted by the owner.

- **FR-001**: The CLI MUST accept exactly one HTTP or HTTPS job-posting URL and explain missing, multiple, or invalid input (Story 3.1).
- **FR-002**: Factual assessment findings MUST come from the target posting's retrieved content; external company research, reviews, and commute information MUST be excluded (agreed scope; Stories 1–2).
- **FR-003**: The report MUST identify the stated work arrangement, preserving multiple options, restrictions, conflicts, or missing information where applicable (Story 1.1–1.6).
- **FR-004**: The report MUST separate source facts from fit judgments and use the supplied preferences: remote preferred, hybrid acceptable. It MUST NOT invent additional preferences, hard exclusions, or personal eligibility (Story 1.1–1.5).
- **FR-005**: For hybrid work, the report MUST state whether home-working days are specified and preserve any stated number/range, period, conditions, and allowance versus expectation (Story 2.1–2.5).
- **FR-006**: Each factual finding MUST identify its source URL and supporting passage. Each fit judgment MUST reference the findings and owner-supplied preference that justify it (Stories 1–2).
- **FR-007**: Missing and conflicting information MUST be explicit, without converting absent evidence into a negative fact or inferring home-working days from an unstated workweek (Story 1.4–1.6; Story 2.3–2.5; Story 3.3).
- **FR-008**: Successful output MUST be readable in the terminal and contain the assessed URL, work-arrangement findings, applicable hybrid home-working details, evidence, fit judgments, and uncertainties. It MUST NOT require saving or managing assessments (Stories 1–2).
- **FR-009**: Invalid input, unavailable or unidentifiable posting content, and failed assessment MUST produce an unsuccessful command outcome and explanatory message without fabricated fit conclusions. Missing criterion details in a readable posting MUST allow an assessment with explicit uncertainty (Story 3.1–3.4).
- **FR-010**: Verification MUST use versioned, manually authored cases containing source material, preferences, expected semantic findings, supporting passages, and prohibited conclusions. Exact wording MUST NOT determine assessment correctness (Success Criteria).
- **FR-011**: Verification MUST record the model/configuration, per-case results, and remaining limitations. Required cases and checks MUST pass before the feature is described as complete (Success Criteria; constitution workflow).

### Key Entities *(include if feature involves data)*

- **Posting source**: The submitted URL and retrieved posting content supporting findings.
- **Job preference**: An owner-authored criterion and its fit meaning; initially remote preferred, hybrid acceptable, and identification of stated hybrid home-working days.
- **Finding**: A source-supported arrangement or schedule detail, including evidence, conditions, conflicts, and uncertainty.
- **Assessment**: Findings, preference-based fit judgments, uncertainties, and the assessed URL.
- **Golden case**: Manually authored source content, expected findings, evidence, and prohibited conclusions. This does not imply runtime storage of assessments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

These are proposed acceptance targets, not claims that assessment validation has run.

- **SC-001**: Across all owner-reviewed golden cases, every required arrangement finding and fit judgment matches the case's semantic expectations, allowing wording to vary.
- **SC-002**: Across all hybrid cases, 100% correctly identify whether home-working days are stated and preserve quantities, periods, allowances, expectations, and conditions.
- **SC-003**: Across all cases, every factual assessment claim is supported by its cited passage, all expected uncertainties/conflicts appear, and there are zero case-defined prohibited conclusions.
- **SC-004**: Every invalid-input and failed-assessment case produces an explanatory failure; every readable posting with missing criterion information produces an assessment identifying that absence.
- **SC-005**: For each successful case, the owner can identify the arrangement, applicable home-working schedule, and reason for each fit judgment from terminal output without consulting another source or saved report.

### Golden-case Requirements

Before implementation acceptance, manually authored cases and expectations must be reviewed by the owner. The scenarios in this specification describe behavior; they are not an existing manually authored golden dataset.

Cases must cover explicit remote, hybrid with an allowance, hybrid with an expectation, hybrid without a schedule, office-days-only wording, explicit on-site work, unspecified arrangement, conflicts, conditional eligibility, and unsuccessful retrieval or assessment. One case may cover multiple conditions. Input cases must cover missing input, invalid URLs, and multiple URLs.

Each case must record required findings and uncertainties, acceptable fit judgments, supporting passages, and prohibited conclusions. Every mandatory expectation must pass; aggregate scores cannot hide a failed expectation. Concrete examples remain to be supplied and reviewed.

## Assumptions

### Agreed Requirements

- One posting URL produces a readable assessment supported by evidence and explicit missing information.
- Remote work is best; hybrid is acceptable; the assessment checks stated allowed/expected hybrid home-working days.
- Manually authored examples define expected behavior.
- External company research, commute estimates, and managing saved assessments are deferred for this feature, remaining possible future capabilities.
- The manually revised constitution remains authoritative and unchanged.

### Proposed Defaults for Owner Review

- Terminal output is sufficient. Report saving, numeric scores, overall apply/reject recommendations, and a configurable criteria interface are not required in this increment.
- On-site work is reported as outside the stated remote/hybrid preferences. No hard exclusion has been supplied, so the tool does not invent one.
- Only the target posting supplies factual evidence; remote restrictions are preserved without deciding personal eligibility.
- Missing arrangement information permits an assessment with uncertainty; unavailable or unidentifiable posting content causes failure.
- Universal job-site support, authenticated pages, bulk/file inputs, and interactive sign-in are not promised. Representative sources must be selected with the examples before technical planning is finalized.

### Dependencies and Review Status

- Actual posting examples and manually authored expected findings are still needed. Their absence is a validation dependency, not permission to invent preferences or claim assessment quality.
- Technical planning must choose retrieval support, language, tooling, model/provider, strict checks, coverage target, external-call test strategy, and criterion separation. This specification makes none of those technical choices.
- Constitution review: simplicity, evidence, actual criteria, CLI scope, and golden-case validation are reflected here. Development practices and criterion separation remain obligations for planning and implementation. No constitutional violation has been identified at this stage.
- Completed work: initial draft and requirements-quality review in `checklists/requirements.md`. No technical planning, tasks, implementation, or assessment evaluation has run.
- Next action: owner reviews the draft, especially proposed defaults and acceptance targets. Then use `$speckit-clarify` to examine remaining material ambiguities before `$speckit-plan`.
