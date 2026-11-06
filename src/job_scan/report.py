"""Readable terminal rendering; values are source findings, not executable markup."""

from job_scan.models import Assessment


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
