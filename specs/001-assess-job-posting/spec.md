# Feature Specification: Assess a Job Posting

**Feature Branch**: `main`
**Feature Directory**: `specs/001-assess-job-posting`
**Created**: 2026-11-05
**Status**: Draft — revised after owner review; input boundary awaiting confirmation

**Input**: Assess a posting against the owner's work-arrangement criteria, with source evidence and explicit uncertainty. The original request accepted a URL. After reviewing that scope, the owner questioned combining fetching with evaluation and specified that realistic assessment input is HTML whose markup may matter. This revision proposes evaluating a saved HTML file first and deferring URL fetching; that scope change is not yet adopted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand work arrangements from posting HTML (Priority: P1)

As a job seeker, I assess a posting's HTML and learn whether it offers remote or hybrid work and, for hybrid, how many work-from-home days are allowed or expected. Remote is preferred; hybrid is acceptable.

**Why this priority**: This answers the first criterion the owner supplied, while allowing evaluation to be developed independently of website retrieval.

**Independent Test**: Assess manually authored HTML examples and compare findings and supporting evidence with their expected meanings, allowing wording to vary.

**Acceptance Scenarios**:

1. **Given** a posting explicitly offering remote work, **When** assessed, **Then** the report cites the supporting content and separately identifies remote as preferred; any stated restrictions remain visible.
2. **Given** hybrid work with an allowed or expected home-working schedule, **When** assessed, **Then** the report identifies hybrid as acceptable and preserves the schedule's quantity, period, conditions, and allowance versus expectation.
3. **Given** missing or conflicting work-arrangement details, **When** assessed, **Then** the report identifies uncertainty or conflicting evidence instead of inventing a definitive arrangement or schedule.
4. **Given** explicit on-site work, **When** assessed, **Then** the report identifies it with evidence, without inventing a hard rejection rule.
5. **Given** HTML whose headings, lists, or table relationships associate different schedules with different roles or locations, **When** assessed, **Then** findings preserve those associations rather than assigning a schedule to the wrong role or location. If the target job cannot be identified, the result explains that ambiguity.
6. **Given** missing/unreadable input, HTML without identifiable posting content, or an unsuccessful assessment, **When** invoked, **Then** the CLI returns an explanatory failure rather than fabricated findings. A posting merely omitting work-arrangement details still receives an assessment with uncertainty.

### Edge Cases

- Office-attendance days alone do not establish home-working days without a stated workweek.
- “Flexible” or occasional home working does not establish a definite remote/hybrid schedule.
- An HTML snapshot containing only a loading shell does not establish facts about the absent posting.

## Requirements *(mandatory)*

### Functional Requirements

These detailed requirements express the revised proposal; the agreed decisions and pending scope change are separated below.

- **FR-001**: The CLI MUST accept one saved HTML file representing a posting. A source URL MAY accompany it for provenance; it MUST NOT trigger fetching in this feature. Invalid or unreadable input MUST produce an explanatory unsuccessful outcome (scenario 6).
- **FR-002**: HTML MUST be accepted without requiring the user to flatten it to plain text. Assessment MUST preserve meaning conveyed by document structure and content relationships; the internal processing method belongs in the technical plan (scenario 5).
- **FR-003**: The report MUST identify the stated arrangement and distinguish it from fit judgments: remote preferred, hybrid acceptable. It MUST preserve restrictions without assuming the user's eligibility or inventing hard exclusions (scenarios 1–4).
- **FR-004**: For hybrid work, the report MUST state whether home-working days are specified and preserve stated numbers/ranges, periods, conditions, and allowed versus expected schedules (scenario 2; edge cases).
- **FR-005**: Factual claims MUST be supported by identifiable passages or elements in the supplied HTML. The report MUST identify the input file and any supplied source URL. Fit judgments MUST refer to supporting findings and the owner's preferences (scenarios 1–5).
- **FR-006**: Missing or conflicting evidence MUST be explicit. Inability to identify or assess a posting MUST produce an explanatory unsuccessful outcome; missing criterion details alone MUST NOT be treated as failure or negative evidence (scenarios 3, 5–6).
- **FR-007**: The terminal report MUST present the work arrangement, applicable hybrid schedule, supporting evidence, fit judgments, and uncertainty (scenarios 1–5).

### Key Entities *(include if feature involves data)*

- **Posting input**: Supplied HTML, its file identity, and optional source URL.
- **Assessment**: Work-arrangement and schedule findings, evidence, preference-based judgments, and uncertainty.
- **Golden case**: Manually authored HTML with expected findings, supporting evidence, and prohibited conclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

Proposed targets for feature acceptance:

- **SC-001**: All required semantic findings and uncertainties in the owner-reviewed golden cases are reported correctly; every factual claim has supporting source evidence and no case-defined prohibited conclusion appears.
- **SC-002**: Structure-sensitive cases correctly associate schedules with the relevant role/location. Include a paired example where changing HTML associations changes the expected finding while retaining the same words.
- **SC-003**: All invalid-input and failed-assessment cases yield explanatory failures; readable postings with missing criterion information yield assessments identifying that absence.
- **SC-004**: The owner can identify the arrangement, stated home-working schedule, and reasons for fit judgments from each successful report.

Golden cases must cover remote, hybrid allowances and expectations, missing schedules, on-site work, uncertainty/conflicts, meaningful HTML structure, and unusable input. Cases can cover several conditions. They are still to be manually authored and reviewed; these scenarios are not a completed dataset. Evaluation must record model/configuration, per-case results, and limitations. Code coverage alone does not establish assessment quality.

## Assumptions

### Agreed Requirements

- Remote is best; hybrid is acceptable; identify stated allowed/expected hybrid home-working days.
- Evaluate HTML from a webpage; markup may carry significant information.
- Findings require evidence, explicit uncertainty, and manually authored examples.
- External company research, commute estimates, and managing saved assessments are deferred.

### Proposed Scope Change and Defaults — Awaiting Review

- Evaluate one saved HTML file first, replacing URL input for this increment. Fetching, browser rendering, authentication, and extraction from live sites belong in a subsequent feature. This is a proposed separation of work, not an adopted abandonment of the URL-based product goal.
- Output is terminal-only, with no numeric score or overall apply/reject recommendation.
- Supplied HTML is the sole factual source. The optional URL records provenance; it is not additional evidence.

### Workflow Status

The constitution is unchanged. This draft supports simplicity, evidence, owner-supplied criteria, CLI use, and golden-case validation. Criterion separation, strict lint/type checks, coverage target, system tests, and external-service test strategy remain obligations for technical planning. No constitutional violation has been identified at this stage.

Current stage: specification review. Confirm the proposed input boundary and supply/review golden examples before technical planning is finalized. Next stage after owner review: `$speckit-clarify`. No plan, tasks, implementation, or model evaluation has run.
