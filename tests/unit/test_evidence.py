import pytest

from job_scan.evidence import resolve, validate_evidence
from job_scan.models import Evidence, WorkArrangementResult


def test_unicode_overlap_locations() -> None:
    html = "é\naaaa\nend"
    resolved = resolve(html, Evidence(quote="aa", occurrence=2))
    assert (resolved.start, resolved.end, resolved.line, resolved.end_line) == (4, 6, 2, 2)
    assert resolve(html, Evidence(quote="aaaa\nend", occurrence=0)).end_line == 3
    for quote, occurrence in (("absent", 0), ("aa", 3)):
        with pytest.raises(ValueError, match="evidence"):
            resolve(html, Evidence(quote=quote, occurrence=occurrence))


def test_validates_all_claims(remote_result: dict[str, object]) -> None:
    result = WorkArrangementResult.model_validate(remote_result)
    assert len(validate_evidence("Fully remote", result)) == 1
    with pytest.raises(ValueError):
        validate_evidence("onsite", result)
    result.home_working = []


def test_schedule_wording_and_failure(remote_result: dict[str, object]) -> None:
    from pathlib import Path

    from job_scan.evidence import AssessmentError, assess
    from job_scan.models import PostingInput, Schedule

    result = WorkArrangementResult.model_validate(remote_result)
    result.home_working = [
        Schedule(
            kind="allowed",
            context="Engineer",
            days_text="3 days",
            period="per week",
            evidence=result.arrangements[0].evidence,
        )
    ]
    with pytest.raises(ValueError, match="wording"):
        validate_evidence("Fully remote", result)
    result.posting_status = "absent"
    result.posting_explanation = "No identifiable posting."
    source = PostingInput(path=Path("input.html"), source_url=None, html="Loading", sha256="fake")
    with pytest.raises(AssessmentError, match="identifiable"):
        assess(source, result, "test")
