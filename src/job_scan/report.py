"""Readable terminal rendering; values are source findings, not executable markup."""

from decimal import ROUND_HALF_UP, Decimal

lazy from job_scan.criteria import DIMENSIONS
lazy from job_scan.models import Assessment
lazy from job_scan.rating_models import PersonalizedAssessment


def safe(text: str) -> str:
    """Keep newlines/tabs and visible characters; drop terminal control sequences."""
    return "".join(c if c in "\n\t" or c.isprintable() else "�" for c in text)


def render(assessment: Assessment) -> str:
    result = assessment.findings
    lines = [f"Source: {assessment.source.path}"]
    if assessment.source.source_url is not None:
        lines.append(f"URL: {assessment.source.source_url}")
    lines += [f"Model: {assessment.model}", "", "Work arrangement:"]
    lines += [f"  {a.kind}: {a.context}" for a in result.arrangements] or ["  Not stated."]
    lines += ["", "Home-working schedule:"]
    for schedule in result.home_working:
        detail = " ".join(p for p in (schedule.days_text, schedule.period) if p is not None)
        lines.append(
            f"  {schedule.kind}: {detail or 'quantity/period not stated'}; {schedule.context}"
        )
    if not result.home_working:
        lines.append("  Not stated or not applicable; no schedule inferred.")
    lines += ["", "Fit:", *(f"  {fit}" for fit in assessment.fit), "", "Evidence:"]
    for evidence in assessment.evidence:
        lines += [
            f"  line {evidence.line}-{evidence.end_line}, chars {evidence.start}:{evidence.end}",
            f"    {evidence.quote}",
        ]
    lines += ["", "Uncertainty:"]
    lines += [f"  {u}" for u in result.uncertainties] or ["  None reported."]
    if result.conflicts:
        lines += ["", "Conflicting evidence:", *(f"  {c.explanation}" for c in result.conflicts)]
    return safe("\n".join(lines)) + "\n"


def render_personalized(assessment: PersonalizedAssessment) -> str:
    """Render once after every required stage has validated."""
    lines = [
        render(assessment.work_arrangement).rstrip(),
        f"Profile: {assessment.profile.path} (SHA-256 {assessment.profile.sha256})",
        "Scores are subjective fit: 0 no fit, 50 mixed, 100 full; not probabilities.",
    ]
    for stage in assessment.passes:
        lines.append(
            f"{stage.stage} model: requested {stage.requested_model}; "
            f"returned {stage.returned_model or 'not reported'}; reasoning {stage.reasoning}"
        )
    labels = {d.id: d.label for d in DIMENSIONS}
    for dimension in assessment.dimensions:
        state = (
            str(dimension.score)
            if dimension.score is not None
            else dimension.status.replace("_", " ")
        )
        lines += [
            "",
            f"{labels[dimension.dimension_id]} ({dimension.dimension_id}):",
            f"  Importance: {dimension.importance}; {state}",
            f"  {dimension.explanation}",
        ]
        for finding in dimension.findings:
            lines.append(f"  Posting fact [{finding.id}]: {finding.statement}")
        for judgment in dimension.judgments:
            lines += [
                f"  Preference excerpt: {judgment.preference_quote}",
                f"  Inferred fit ({judgment.polarity}; "
                f"findings {', '.join(judgment.finding_ids)}): "
                f"{judgment.explanation}",
            ]
        for evidence in dimension.evidence:
            lines += [
                f"  Source line {evidence.line}-{evidence.end_line}, "
                f"chars {evidence.start}:{evidence.end}: {evidence.quote}"
            ]
        lines += [f"  Uncertainty: {u}" for u in dimension.uncertainties]
        lines += [f"  Conflict: {c.explanation}" for c in dimension.conflicts]
    overall = assessment.overall
    lines += ["", "Weighted overall (work arrangement excluded):"]
    if overall.value is None:
        lines.append("  Unavailable: no configured dimensions could be rated.")
    else:
        label = "Partial overall" if overall.status == "partial" else "Complete overall"
        lines.append(
            f"  {label}: {one_decimal(overall.value)}/100; "
            f"{overall.numerator} / {overall.denominator}"
        )
        for contribution in overall.contributions:
            lines.append(
                f"  {labels[contribution.dimension_id]}: {contribution.importance} * "
                f"{contribution.score} = {contribution.numerator}; "
                f"approximate contribution {one_decimal(contribution.value)}"
            )
    lines += [
        f"  Dimensions rated: {overall.rated_dimension_count}/"
        f"{overall.configured_dimension_count}; "
        f"importance coverage: {overall.rated_importance}/{overall.total_configured_importance}"
    ]
    for dimension in assessment.dimensions:
        if dimension.dimension_id in overall.missing_dimension_ids:
            lines.append(f"  Missing {labels[dimension.dimension_id]}: {dimension.explanation}")
    outcomes = {
        "conflicting_exceptions": "conflicting exceptions",
        "worth_pursuing_despite_weaknesses": "worth pursuing despite weaknesses",
        "deal_breaker": "deal-breaker",
        "unresolved_exceptions": "unresolved exceptions",
        "no_exception_applies": "no exceptional preference applies",
    }
    lines += ["", f"Decisive outcome: {outcomes[assessment.decisive.code]}"]
    if assessment.decisive.matched_ids and assessment.decisive.unresolved_ids:
        lines.append("  Outcome based on confirmed matches only; unresolved conditions remain.")
    if assessment.decisive.code == "conflicting_exceptions":
        lines.append("  Both exceptional types match; the user decides how to proceed.")
    for item in assessment.decisive.exceptions:
        lines += [
            f"  {item.declaration.id}: {item.declaration.kind.replace('_', ' ')}; "
            f"{item.match.status.replace('_', ' ')}",
            f"  Preference excerpt: {item.declaration.preference_quote}",
            f"  {item.match.explanation}",
        ]
        for evidence in item.evidence:
            lines.append(
                f"  Source line {evidence.line}-{evidence.end_line}, "
                f"chars {evidence.start}:{evidence.end}: {evidence.quote}"
            )
    return safe("\n".join(lines)) + "\n"


def one_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
