"""Functional core: context validation, source resolution, and weighted arithmetic."""

from decimal import Decimal

from job_scan.criteria import DIMENSIONS
from job_scan.evidence import resolve
from job_scan.models import Assessment, Evidence, ResolvedEvidence
from job_scan.profiles import ProfileInput
from job_scan.rating_models import (
    Contribution,
    DecisiveOutcome,
    DimensionOutcome,
    EvaluatedException,
    ExceptionResponse,
    FitResponse,
    PassMetadata,
    PersonalizedAssessment,
    WeightedOverall,
)


def resolve_unique(html: str, evidence: list[Evidence]) -> list[ResolvedEvidence]:
    return [
        resolve(html, Evidence(quote=q, occurrence=o))
        for q, o in dict.fromkeys((e.quote, e.occurrence) for e in evidence)
    ]


def aggregate(dimensions: list[DimensionOutcome]) -> WeightedOverall:
    configured = [d for d in dimensions if d.status != "not_configured"]
    rated = [d for d in configured if d.score is not None]
    missing = [d.dimension_id for d in configured if d.score is None]
    denominator = sum(d.importance for d in rated)
    contributions = [
        Contribution(
            dimension_id=d.dimension_id,
            importance=d.importance,
            score=d.score,
            numerator=d.importance * d.score,
            value=Decimal(d.importance * d.score) / denominator,
        )
        for d in rated
        if d.score is not None
    ]
    numerator = sum(c.numerator for c in contributions)
    return WeightedOverall(
        status=("partial" if missing else "available") if rated else "unavailable",
        numerator=numerator if rated else None,
        denominator=denominator if rated else None,
        value=Decimal(numerator) / denominator if rated else None,
        missing_dimension_ids=missing,
        rated_dimension_count=len(rated),
        configured_dimension_count=len(configured),
        rated_importance=denominator,
        total_configured_importance=sum(d.importance for d in configured),
        contributions=contributions,
    )


def assemble(
    work: Assessment,
    profile: ProfileInput,
    response: FitResponse,
    passes: list[PassMetadata],
    exceptions: ExceptionResponse | None = None,
) -> PersonalizedAssessment:
    outcomes = build_dimensions(work, profile, response)
    evaluated = validate_exceptions(work.source.html, profile, exceptions)
    for dimension in outcomes:
        ids = {item.id for item in profile.profile.dimensions[dimension.dimension_id].exceptions}
        dimension.exceptions = [item for item in evaluated if item.declaration.id in ids]
    return PersonalizedAssessment(
        work_arrangement=work,
        profile=profile,
        dimensions=outcomes,
        overall=aggregate(outcomes),
        decisive=decisive_outcome(evaluated),
        passes=passes,
    )


def build_dimensions(
    work: Assessment, profile: ProfileInput, response: FitResponse
) -> list[DimensionOutcome]:
    configured = {name for name, d in profile.profile.dimensions.items() if d.preferences.strip()}
    ids = [d.dimension_id for d in response.dimensions]
    if set(ids) != configured or len(ids) != len(configured):
        raise ValueError("Fit response must cover exactly the configured dimension IDs.")
    fits = {d.dimension_id: d for d in response.dimensions}
    outcomes = []
    for definition in DIMENSIONS:
        dimension = profile.profile.dimensions[definition.id]
        fit = fits.get(definition.id)
        if fit is None:
            outcomes.append(
                DimensionOutcome(
                    dimension_id=definition.id,
                    importance=dimension.importance,
                    status="not_configured",
                    score=None,
                    explanation="No preferences configured.",
                    findings=[],
                    judgments=[],
                    uncertainties=[],
                    conflicts=[],
                    evidence=[],
                    exceptions=[],
                )
            )
            continue
        for judgment in fit.judgments:
            if judgment.preference_quote not in dimension.preferences:
                raise ValueError("Preference excerpt does not match requested dimension prose.")
        evidence = [e for f in fit.findings for e in f.evidence]
        evidence += [e for c in fit.conflicts for e in c.evidence]
        outcomes.append(
            DimensionOutcome(
                **fit.model_dump(),
                importance=dimension.importance,
                evidence=resolve_unique(work.source.html, evidence),
                exceptions=[],
            )
        )
    return outcomes


def validate_exceptions(
    html: str, profile: ProfileInput, response: ExceptionResponse | None
) -> list[EvaluatedException]:
    declarations = [
        item for d in DIMENSIONS for item in profile.profile.dimensions[d.id].exceptions
    ]
    results = response.exceptions if response is not None else []
    ids = [item.exception_id for item in results]
    if set(ids) != {d.id for d in declarations} or len(ids) != len(declarations):
        raise ValueError("Exception response must cover exactly the supplied declaration IDs.")
    by_id = {item.exception_id: item for item in results}
    return [
        EvaluatedException(
            declaration=declaration,
            match=by_id[declaration.id],
            evidence=resolve_unique(html, by_id[declaration.id].evidence),
        )
        for declaration in declarations
    ]


def decisive_outcome(exceptions: list[EvaluatedException]) -> DecisiveOutcome:
    matched = [e for e in exceptions if e.match.status == "matched"]
    unresolved = [e.declaration.id for e in exceptions if e.match.status == "unresolved"]
    kinds = {e.declaration.kind for e in matched}
    if len(kinds) == 2:
        code = "conflicting_exceptions"
    elif "compelling_attraction" in kinds:
        code = "worth_pursuing_despite_weaknesses"
    elif "deal_breaker" in kinds:
        code = "deal_breaker"
    else:
        code = "unresolved_exceptions" if unresolved else "no_exception_applies"
    return DecisiveOutcome(
        code=code,
        matched_ids=[e.declaration.id for e in matched],
        unresolved_ids=unresolved,
        exceptions=exceptions,
    )
