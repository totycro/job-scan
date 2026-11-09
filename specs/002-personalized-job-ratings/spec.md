# Feature Specification: Personalized Job Ratings

**Feature Branch**: `main`

**Feature Directory**: `specs/002-personalized-job-ratings`

**Created**: 2026-11-09

**Status**: Draft — clarification complete; ready for planning

**Input**: Add advanced LLM-based job-posting ratings for role fit, technology fit, interest in the company's field, and affinity for the company. These are four new dimensions alongside the existing work-arrangement dimension (remote/hybrid/on-site); the assessment model can grow with future dimensions. Users first write their individual preferences/profiles in files and assign importance to each new dimension so the assessment reflects their priorities.

## Clarifications

### Session 2026-11-09

- Q: How should an exceptional preference affect the overall result? → A: Keep the weighted score unchanged and add a separate decisive outcome, such as “worth pursuing despite weaknesses” or “deal-breaker,” with reasons. General dimension importance remains 0–5.
- Q: If a posting matches both a compelling attraction and a deal-breaker, which should determine the decisive outcome? → A: Report “conflicting exceptions,” show both matches with evidence, and leave the decision to the user; neither takes automatic precedence.
- Q: Does “four dimensions” describe the complete assessment model? → A: No. This feature adds four new dimensions alongside the existing work-arrangement dimension (remote/hybrid/on-site); more dimensions will be added in future features.

- Q: How should missing dimension evidence affect the overall score? → A: Show a weighted score from the rated enabled dimensions, mark it partial, and list missing dimensions and coverage. If none can be rated, show no numeric overall score.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rate a posting against my written preferences (Priority: P1)

As a job seeker, I write a reusable preference file describing the role I want, my technology knowledge and interests, fields I find interesting, and what makes a company appealing or unappealing. I supply it when assessing a saved posting and receive separate, explained ratings grounded in my preferences and the posting.

**Why this priority**: A generic judgment cannot answer whether a job is suitable for a particular person. Written profiles make the user's own criteria the basis of the assessment.

**Independent Test**: Assess the same manually authored posting with two contrasting profiles and verify that each explanation and rating follows its supplied profile and the available evidence.

**Acceptance Scenarios**:

1. **Given** a valid preference file and a posting with relevant evidence for all four new dimensions, **When** I request personalized assessment, **Then** I receive a separate rating and explanation for role fit, technology fit, field interest, and company affinity, each linking the relevant preferences to cited posting evidence.
2. **Given** a posting that strongly matches one person's desired responsibilities and conflicts with another's, **When** assessed with each profile, **Then** the role ratings reflect the different preferences without changing the reported posting facts.
3. **Given** a profile that distinguishes technologies I already know from technologies I want to learn or avoid, **When** a posting names technologies, **Then** the technology explanation distinguishes existing knowledge from interest in learning and does not assume that unfamiliarity means dislike or that familiarity means preference.
4. **Given** interest in a company's field but dislike of its stated operating practices, **When** assessed, **Then** field interest and company affinity remain separate findings and can receive different ratings.
5. **Given** an edited profile file, **When** I assess the posting again, **Then** the assessment uses the edited preferences without requiring code changes or an account profile update.

---

### User Story 2 - Make the overall rating reflect my priorities (Priority: P2)

As a job seeker, I assign relative importance to each of the four new dimensions so that a technology-focused search, a field-focused search, and a balanced search yield appropriately different overall ratings. I can also explicitly identify individual preferences as compelling attractions or deal-breakers, producing a separate decisive outcome without changing the weighted calculation.

**Why this priority**: Separate ratings explain tradeoffs; personal importance determines how those tradeoffs contribute to an overall judgment.

**Independent Test**: Hold dimension ratings constant and apply technology-heavy, field-heavy, and equal weights. Verify the displayed overall rating and contributions against the declared weighting rule.

**Acceptance Scenarios**:

1. **Given** equal positive importance for all four new dimensions, **When** all four new dimensions are rated, **Then** each contributes equally to the overall rating.
2. **Given** higher importance for technology fit than field interest, **When** a posting has strong technology fit and weak field interest, **Then** the overall rating reflects the greater technology contribution; reversing those weights reverses their relative contributions.
3. **Given** zero importance for a new dimension, **When** assessed, **Then** it is shown as disabled, requires no profile text, and contributes nothing to the overall rating.
4. **Given** unchanged dimension ratings and increased importance for an above-average dimension, **When** the overall rating is recalculated, **Then** the overall rating does not decrease.
5. **Given** negative, non-numeric, out-of-range, or all-zero importance values, **When** personalized assessment is requested, **Then** it fails with actionable profile-validation feedback before requesting an assessment.
6. **Given** an explicitly declared compelling attraction to a particular field and posting evidence that it applies, with no matched deal-breaker, **When** other dimensions rate poorly, **Then** the report states “worth pursuing despite weaknesses,” citing that preference and evidence while preserving the weighted score.
7. **Given** an explicitly declared deal-breaker technology and evidence that the role requires it, with no matched compelling attraction, **When** other dimensions rate highly, **Then** the report states “deal-breaker,” citing that preference and evidence while preserving the weighted score.
8. **Given** ordinary positive or negative preferences without explicit exceptional status, **When** assessed, **Then** the system does not invent a compelling attraction or deal-breaker from the intensity of its own judgment.
9. **Given** an exceptional preference whose applicability lacks sufficient evidence, **When** assessed, **Then** it is reported as unresolved rather than matched or disproved; a partial weighted score remains labeled partial, and an unavailable weighted score remains unavailable, even when another exceptional preference is supported.
10. **Given** posting evidence matching both a declared compelling attraction and a declared deal-breaker, **When** assessed, **Then** the decisive outcome is “conflicting exceptions,” both matches and their evidence are shown, the weighted score remains unchanged, and neither exception is automatically preferred.

---

### User Story 3 - Understand gaps and correct profile problems (Priority: P3)

As a job seeker, I can distinguish lack of fit from lack of information, correct unusable profile files, and continue using the existing assessment when I do not request personalized ratings.

**Why this priority**: Unsupported confidence and silent configuration mistakes would make personalized scores misleading.

**Independent Test**: Use missing-evidence postings, invalid profiles, failed assessments, and the existing invocation without a profile; verify explicit outcomes for each.

**Acceptance Scenarios**:

1. **Given** an active company-affinity dimension but no evidence relevant to its preferences, **When** assessed, **Then** that dimension is marked insufficient evidence without a numeric rating; the report lists company affinity as missing and, if another enabled dimension is rated, shows a partial overall numeric rating based only on rated dimensions; if none is rated, no overall numeric rating is shown.
2. **Given** evidence supporting only part of a dimension's profile, **When** assessed, **Then** apply the FR-006 sufficiency rule: rate only if the explanation supports a dimension-level judgment without assumptions about unassessed preferences; otherwise retain supported findings and mark insufficient evidence. In both cases identify supported and unassessed preferences.
   - **Sufficient partial evidence example:** Preferences say “I want hands-on backend development; occasional mentoring is a nice-to-have.” The posting explicitly describes hands-on backend responsibilities but says nothing about mentoring. A role-fit rating may be supported by the stated main responsibility; the explanation must leave mentoring unknown and explain why that optional detail does not prevent the judgment.
   - **Insufficient partial evidence example:** Preferences say “I want hands-on backend development only if the role has no line-management duties.” The posting describes backend development but gives no information about line management. Preserve the backend match, leave the condition unresolved, and return insufficient evidence for role fit; silence cannot establish that the condition is satisfied. Neither example declares an exceptional preference.
3. **Given** contradictory posting evidence or conflicting preferences, **When** assessed, **Then** the report identifies the conflict and explains any supported judgment; an unresolved conflict preventing a justified rating leaves the dimension unrated.
4. **Given** a missing, unreadable, malformed, or invalid profile, **When** personalized assessment is requested, **Then** the CLI identifies the file and relevant problem and emits no successful personalized report.
5. **Given** no preference file is supplied, **When** the existing saved-HTML assessment is run, **Then** its work-arrangement behavior remains available without requiring profiles or adding personalized scores.
6. **Given** a failed model request or an invalid assessment response, **When** personalized assessment is requested, **Then** the CLI reports failure rather than presenting fabricated or incomplete output as a successful assessment.

### Edge Cases

- A posting mentions a client or recruiting agency in a different field from the hiring company: do not attribute that field or the agency's practices to the employer without evidence.
- A company name alone does not establish its reputation, values, or field. Explicit user preferences about a named company may apply when its identity is evidenced, but user beliefs are not independently verified facts.
- A posting omits a technology: omission alone does not establish that the technology is absent from the role.
- All active dimensions lack evidence: show their uncertainty and no overall numeric rating; this is an assessment with insufficient evidence, not an input failure.
- Explicit exceptional preferences can affect the separate decisive outcome, even when their dimension has low positive importance. A zero-importance dimension remains disabled, including its exceptional preferences. Ordinary dislikes do not automatically become deal-breakers.
- A matched compelling attraction and a matched deal-breaker yield “conflicting exceptions,” whether they belong to the same dimension or different dimensions. Dimension importance does not resolve this conflict; the user decides.
- Posting text contains instructions to ignore the profile or change scores: treat it as source content, not instructions governing the assessment.
- Separate invocations use different profiles: each report must identify the supplied profile and must not inherit preferences from another invocation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST allow a user to explicitly supply a local, human-editable preference file alongside the existing saved-HTML posting input. Personalized ratings MUST be opt-in; without a profile the existing assessment behavior MUST remain available (stories 1 and 3).
- **FR-002**: The preference file MUST support the four new, separately identifiable dimensions introduced by this feature: desired role/responsibilities; technology knowledge and interests; interest in the company's field; and company affinity. Each of these new dimensions MUST have an importance value and, when enabled, nonblank free-text preferences. Users MUST NOT need code changes to edit preferences or importance (story 1).
- **FR-003**: Users MUST receive a documented starter profile and guidance explaining each dimension, valid importance values, and the difference between technology knowledge and learning preferences, and how to explicitly declare a compelling attraction or deal-breaker for an individual preference. Placeholder guidance MUST be distinguishable from actual user preferences; the starter MUST explain how to replace it before assessment (story 1).
- **FR-004**: For each of the four new dimensions, importance MUST be an integer from 0 through 5: 0 disables the dimension, and 1–5 express increasing relative importance. All four new dimension importance values MUST be explicit; at least one MUST be positive. Invalid values, missing required text, duplicate dimension definitions, unknown dimension names, and unreadable or malformed files MUST produce actionable errors before any model assessment request. The user's files MUST NOT be rewritten by assessment (stories 1–3).
- **FR-005**: The system MUST use LLM-based interpretation of the written preferences and posting to rate each enabled new dimension separately on a 0–100 scale, where 0 means no fit, 50 means mixed fit, and 100 means full fit. Ratings are subjective fit judgments, not probabilities or verified facts. Disabled dimensions MUST be labeled and MUST NOT be assessed (stories 1–2).
- **FR-006**: Each rated dimension MUST include its score, importance, relevant user preferences, explanation of matches and mismatches, identifiable supporting posting passages, and any missing or conflicting information. The report MUST distinguish factual evidence, user statements, and inferred fit. Insufficient evidence MUST yield an explicit unrated state rather than a neutral or negative substitute score. A dimension MAY be rated from partial evidence only when the explanation supports a dimension-level fit judgment using the evidenced preferences without assuming facts about unassessed preferences. It MUST identify the supported and unassessed preferences and explain why the missing or conflicting information does not prevent that judgment. If a score would require assuming how an unassessed preference is satisfied or resolving an unsupported conflict, the dimension MUST be `insufficient_evidence`, retaining supported findings but no score. A source quote and a preference match alone do not establish sufficiency. This is a qualitative semantic-review rule, not a numeric preference-coverage threshold. (stories 1 and 3).
- **FR-007**: The overall numeric rating MUST remain independent of the separate decisive outcome and MUST be the weighted arithmetic mean of rated enabled dimensions among the four new dimensions, displayed to one decimal place. Weights need not sum to a prescribed total. If all enabled dimensions are rated, the score is complete. If some but not all are rated, the report MUST show the numeric score clearly labeled “partial,” list every missing dimension and its reason, and show rated/enabled dimension counts and rated/total enabled importance. The denominator MUST be the sum of importance of rated dimensions only; missing scores MUST NOT become zero or an invented score. The report MUST expose the included weights, numerator, denominator, and individual contributions, making the exclusion of missing dimensions explicit. If no enabled dimension is rated, no numeric overall score or normalized contributions are available and every missing dimension MUST be listed (stories 2–3).
- **FR-008**: Supplied HTML MUST remain the sole factual source for the posting and company in this increment. An optional source URL MUST remain provenance only. The assessment MUST NOT use unsupported model recollection or treat profile assertions as verified company facts. Existing HTML-structure and evidence requirements MUST apply to the new dimensions (stories 1 and 3; edge cases).
- **FR-009**: The terminal report MUST identify the posting and supplied preference file and display the four new dimension outcomes, explanations, importance values, overall numeric outcome, and a separate decisive outcome with any supporting exceptional preferences. The existing work-arrangement dimension and its findings MUST remain available and MUST NOT enter this feature's weighted score or be reinterpreted through these profiles (stories 1–3).
- **FR-010**: Profile validation errors, invalid posting input, model-request failures, and unusable model responses MUST produce explanatory unsuccessful outcomes without a successful personalized report. Missing criterion evidence alone MUST yield a successful report with explicit uncertainty and the overall-rating behavior in FR-007 (story 3).
- **FR-011**: Preference content MUST be used only for the requested assessment. Reports MUST include relevant preference excerpts rather than reproduce the full profile unnecessarily; routine diagnostics MUST NOT dump profile contents. Usage guidance MUST state that relevant profile content is sent to the assessment model (stories 1 and 3).
- **FR-012**: Acceptance MUST include manually authored golden postings, contrasting profiles, and expected supported judgments and prohibited conclusions. Evaluation MUST record the model/configuration, per-case results, and remaining limitations; assessment quality MUST NOT be inferred from code coverage alone (all stories).
- **FR-013**: Within each enabled new dimension, users MUST be able to explicitly declare individual preference conditions as compelling attractions or deal-breakers. These declarations MUST be optional and distinct from ordinary preferences and from the dimension's 0–5 importance. The system MUST NOT infer exceptional status merely from an ordinary preference or a high/low dimension score. Declarations in a disabled dimension MUST NOT be evaluated (story 2).
- **FR-014**: For every evaluated exceptional preference, the report MUST identify its declared condition and type, whether it is matched, not matched, or unresolved, and the evidence or uncertainty justifying that finding. Posting omission MUST NOT establish that a deal-breaker is absent. A supported compelling attraction without a matched deal-breaker MUST produce “worth pursuing despite weaknesses”; a supported deal-breaker without a matched compelling attraction MUST produce “deal-breaker.” If both types match, the decisive outcome MUST be “conflicting exceptions,” MUST show the matched conditions and their evidence, and MUST leave the decision to the user without choosing a winner based on importance or numeric scores. If no preference matches and none is unresolved, report “no exceptional preference applies”; if no preference matches but at least one is unresolved, report “unresolved exceptions.” Unresolved conditions MUST remain visible alongside any supported decisive outcome, which MUST be identified as based on confirmed matches only. The underlying preference content still informs ordinary dimension fit; declaring it exceptional MUST NOT itself add bonuses, penalties, caps, or floors to numeric scores. A decisive outcome MAY be supported alongside a partial overall numeric rating or when no overall numeric rating is available; it MUST NOT imply that missing information has been resolved (stories 2–3).

- **FR-015**: The assessment model MUST recognize work arrangement (remote/hybrid/on-site) as an existing dimension and the four dimensions in FR-002 as additions. Four MUST NOT be treated as a permanent total for assessment dimensions. Future features MUST be able to add separately identifiable dimensions while preserving the meanings and findings of existing dimensions; runtime user-defined dimensions are not required by this feature. This increment adds numeric scoring, profile importance, and exceptional preferences only for the four new dimensions (stories 1–3).

### Key Entities *(include if feature involves data)*

- **Preference profile**: User-authored file containing the four new dimension definitions, their free-text preferences, optional exceptional preferences, and relative importance; explicitly selected for an assessment.
- **Assessment dimension**: A separately identifiable aspect of job suitability. Work arrangement is an existing dimension; role fit, technology fit, field interest, and company affinity are the four additions in this feature. Future features may add more. Numeric scoring and profile support are capabilities of a dimension, not prerequisites for recognizing it as a dimension.
- **Preference dimension**: An assessment dimension with user-written preferences and importance; this feature introduces that support for the four new dimensions, with their enabled states and exceptional preferences.
- **Exceptional preference**: An explicitly user-declared condition within a dimension, its compelling-attraction or deal-breaker type, assessed applicability, supporting evidence, and uncertainty. It affects the separate decisive outcome rather than numeric scoring.
- **Posting input**: Existing saved HTML and optional provenance URL; the sole factual evidence source.
- **Dimension rating**: A score or explicit disabled/insufficient-evidence state, related preferences, evidence, explanation, and uncertainty for one dimension.
- **Personalized assessment**: Posting/profile identities, the existing work-arrangement findings, the four new dimension outcomes, weights, contributions, and overall rating or reason it is unavailable, and separate decisive outcome with reasons.
- **Golden case**: Manually authored posting/profile pair with expected fit judgments, supporting evidence, uncertainties, and prohibited conclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can edit the documented starter into a valid personal profile and assess a posting without changing code; each successful report lets the owner identify all four new dimension outcomes, their reasons, and their importance values.
- **SC-002**: In owner-reviewed golden cases, 100% of required matches, mismatches, and uncertainties are correctly reported, every factual claim has supporting source evidence, and no case-defined prohibited conclusion appears. Include at least one contrasting-profile pair per new dimension and explicit coverage of known versus desired technologies and field interest versus company affinity.
- **SC-003**: In all weighting checks, displayed overall ratings agree with the weighted mean within the stated rounding precision. Equal weights, unequal weights, zero weights, and reversed technology/field priorities produce their prescribed results when dimension ratings are held fixed.
- **SC-004**: All missing-evidence cases preserve unknown states without fabricated scores; cases with some rated and some unrated enabled dimensions show a partial weighted mean over rated dimensions, all missing dimensions and reasons, and dimension-count/importance coverage. Cases with no rated enabled dimensions show no numeric overall rating.
- **SC-005**: All specified invalid-profile and failed-assessment cases produce actionable failures with no successful personalized report; all invalid profiles are rejected before requesting an assessment.
- **SC-006**: Existing golden work-arrangement cases continue to meet their accepted outcomes without a profile. With a profile, the work-arrangement findings remain outside the personalized weighted score.
- **SC-007**: Golden cases cover a compelling attraction with weak ratings elsewhere, a deal-breaker with strong ratings elsewhere, ordinary preferences without exceptional declarations, unresolved applicability, exceptions within disabled dimensions, and simultaneous matches for compelling attractions and deal-breakers within the same dimension and across different dimensions. Simultaneous matches MUST yield “conflicting exceptions” with both sides visible and no automatic winner. All required outcomes and evidence judgments MUST be correct; adding, removing, or changing only exceptional declarations MUST leave the serialized ordinary scoring request identical when the HTML, enabled dimensions, preference prose, model/configuration, prompts, and schema are unchanged. With fixed or replayed dimension results and unchanged weights, ordinary scores and the weighted calculation MUST remain identical. Independent live calls MAY produce different subjective scores; cross-run numeric equality is not an acceptance requirement.

- **SC-008**: Reports for personalized assessments identify five dimensions in this increment: the existing qualitative work-arrangement dimension and the four new dimensions with their score or disabled/insufficient-evidence state. No report labels the four new dimensions as the complete set of assessment dimensions.

## Assumptions

- This feature adds personalized ratings end to end; writing files is the initial user setup step, not the entire feature. The first version uses one explicitly selected profile file containing all four new dimensions. Splitting a profile across files, automatic discovery, and profile-management interfaces are deferred.
- The 0–5 importance scale is confirmed as the general weighting factor. The 0–100 integer rating scale and weighted mean are required for this feature. Per the owner's clarification, missing dimension evidence produces an explicitly partial mean over rated enabled dimensions with visible coverage; no numeric mean is available when none is rated. Importance governs ordinary numeric tradeoffs; explicit exceptional preferences govern a separate decisive outcome. Opposing matched exceptions are reported as a conflict for the user to resolve, with no automatic precedence.
- Role preferences may describe responsibilities, seniority, and career direction. Technology preferences may describe proficiency, interest, willingness to learn, and avoidance. Field preferences concern the employer's business domain; company affinity concerns the user's preferences about that employer, including stated practices or explicit named-company preferences.
- No additional company research is included. Useful field/company ratings depend on relevant posting evidence; absent evidence is an expected result. External retrieval, factual company dossiers, and reputation/review gathering require a later feature.
- This increment extends feature 001's scoring exclusion for these four new dimensions only. Work arrangement remains an existing assessment dimension with its current qualitative behavior and is outside this increment’s numeric score. Its saved-HTML input, provenance behavior, authentication, work-arrangement boundaries, and terminal workflow remain the baseline.
- Numeric scores support personal comparison and are not calibrated probabilities, hiring predictions, or automatic application actions. Separate decisive outcomes communicate explicitly declared user exceptions; the user retains the decision whether to apply. Cross-run wording and subjective scores may vary; golden-case judgments and evidence, rather than exact wording or exact model scores, determine semantic acceptance.
- Multi-posting ranking, saved-report management, learned preferences, interactive interviews, implementing dimensions beyond these four additions, and changing work-arrangement preferences or adding numeric scoring to work arrangement are excluded from this increment. Additional dimensions are expected in future features; the overall assessment model is not limited to these four new dimensions.
- Technical file syntax, command options, model/provider configuration, processing organization, and operational limits belong in planning. The existing assessment service is a dependency; manually authored profile/posting cases and owner review are required before feature acceptance.
- Constitution review: the scope preserves CLI use, simple fixed criteria, source evidence, explicit uncertainty, and golden-case validation. Criterion separation and the required development checks remain obligations for planning. No constitutional amendment is needed.
