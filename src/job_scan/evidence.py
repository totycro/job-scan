"""Pure evidence validation and assessment assembly."""

from job_scan.criteria.work_arrangement import fit_judgments
from job_scan.models import (
    Assessment,
    Evidence,
    PostingInput,
    ResolvedEvidence,
    WorkArrangementResult,
)


def resolve(html: str, evidence: Evidence) -> ResolvedEvidence:
    start = -1
    for _ in range(evidence.occurrence + 1):
        start = html.find(evidence.quote, start + 1)
        if start < 0:
            raise ValueError("Source evidence quote or occurrence does not match the HTML.")
    end = start + len(evidence.quote)
    return ResolvedEvidence(
        **evidence.model_dump(),
        start=start,
        end=end,
        line=html.count("\n", 0, start) + 1,
        end_line=html.count("\n", 0, end - 1) + 1,
    )


def validate_evidence(html: str, result: WorkArrangementResult) -> list[ResolvedEvidence]:
    evidence = [*a.evidence for a in result.arrangements]
    evidence += [*schedule.evidence for schedule in result.home_working]
    evidence += [*conflict.evidence for conflict in result.conflicts]
    for schedule in result.home_working:
        if schedule.days_text is not None and not any(
            schedule.days_text in e.quote for e in schedule.evidence
        ):
            raise ValueError("Home-working quantity must reproduce cited source wording.")
    unique = dict.fromkeys((e.quote, e.occurrence) for e in evidence)
    return [
        resolve(html, Evidence(quote=quote, occurrence=occurrence)) for quote, occurrence in unique
    ]


class AssessmentError(RuntimeError):
    """Source-specific unsuccessful assessment explanation."""


def assess(source: PostingInput, result: WorkArrangementResult, model: str) -> Assessment:
    if result.posting_status != "identified":
        raise AssessmentError(
            result.posting_explanation or "Unable to identify the target posting."
        )
    return Assessment(
        source=source,
        findings=result,
        evidence=validate_evidence(source.html, result),
        fit=fit_judgments(result),
        model=model,
    )
