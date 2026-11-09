<!--
Sync Impact Report (temporary amendment review notes; remove before commit)
Version change: 1.0.0 -> 1.1.0
Modified principles: IV. Development practices (title unchanged)
Added sections: None
Removed sections: None
Reason: Make the owner's reproducible, uv-only environment policy explicit for future planning.
Impact: Plans and implementations must use exact dependency pins and the locked uv workflow.
Existing pyproject.toml, uv.lock, README.md, and AGENTS.md already reflect this policy.
Assessment behavior is unchanged. Templates and commands read this constitution at runtime.
Follow-up TODOs: None
-->
# job-scan Constitution

## Core Principles

### I. Keep it simple

This is a small project for personal use, not an enterprise software that needs to support a massive amount of concurrent users. If in doubt, choose the simpler solution.

### II. Evidence and Explicit Uncertainty

Factual claims about a posting, company, reviews, or commute MUST be traceable to retrieved
source material. Assessments MUST distinguish source facts from inferred fit judgments and
identify unavailable or conflicting information. Missing evidence MUST NOT be converted into
an invented fact or a confident conclusion.

### III. Job criteria

There are a number of criteria by which job postings are evaluated. Keep criterion-specific logic separate so changing one criterion does not require modifying unrelated criteria. Runtime configuration of criteria is not necessary.

### IV. Development practices

The technical plan MUST select strict linting and type-checking settings and define a coverage target. Required checks MUST pass before feature completion.
Prefer TDD and Imperative shell/functional core architecture.
Maintain a small set of end-to-end tests covering the primary CLI workflows. Exercise real internal components; the technical plan MUST define which external services use recorded responses or live calls.

This tool is not meant to support a wide range of installation, only `uv run --locked` is officially supported. Use exact version pins in `pyproject.toml` with `==` to ensure reprocability and pin transitive dependencies with `uv.lock`.

### V. UI

Main UI is CLI for now. Something more fancy might follow.

### VI. Validation

We keep a number of manually authored cases as golden dataset. 


## Product Boundaries

job-scan helps a user understand job postings against their own criteria. Role fit, company
information, technology interests, satisfaction data, and commute information are candidate
capabilities; this list does not require them all in the first release.

Each feature spec MUST define its supported inputs, information sources, output behavior,
failure handling, and exclusions. Managing assessments over a job search remains an open
product decision until addressed by a feature spec. Language, framework, model provider, and
storage choices belong in technical plans and are not fixed by this constitution.

## Development Workflow

1. Define the feature's user outcomes, scope, acceptance scenarios, and open questions with
   Spec Kit's specify step. Resolve material ambiguities before technical planning.
2. Produce a technical plan that checks compliance with every core principle and records
   design choices and their rationale.
3. Break the plan into tasks that include relevant curated examples and verification work.
4. Implement against the spec and plan. Update those artifacts when an intentional behavior
   change alters their requirements or design.
5. Verify deterministic behavior with appropriate automated tests. Evaluate LLM findings
   against the relevant golden examples using feature-defined acceptance criteria; document
   the model and configuration used, results, and remaining limitations.
6. Run the convergence step to identify gaps between the implementation, spec, plan, and tasks.
   Do not describe a feature as complete while required behavior or verification is missing.

Changes that do not affect assessment behavior require checks appropriate to their impact;
they do not require an unrelated full LLM evaluation run.

## Governance

This constitution governs feature specs, technical plans, tasks, and implementation reviews.
Each feature review MUST check compliance and record unresolved violations. A conflict MUST
be resolved by changing the work or explicitly amending the constitution; it MUST NOT be
silently ignored.

Amendments MUST state the reason, affected principles, and impact on existing artifacts or
behavior. The project owner reviews amendments before adoption. Amendments MUST update the
version and last-amended date while preserving the original ratification date.

Use semantic versioning: MAJOR for incompatible changes to or removal of existing principles,
MINOR for new principles or materially expanded guidance, and PATCH for clarifications that do
not change obligations. This initial adoption establishes version 1.0.0.

**Version**: 1.1.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-09
