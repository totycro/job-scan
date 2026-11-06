from pathlib import Path

from job_scan.evidence import assess
from job_scan.models import PostingInput, WorkArrangementResult
from job_scan.report import render


def test_report(remote_result: dict[str, object]) -> None:
    source = PostingInput(
        path=Path("posting.html"),
        source_url="https://example.com/job",
        html="Fully remote",
        sha256="example",
    )
    result = WorkArrangementResult.model_validate(remote_result)
    report = render(assess(source, result, "test-model"))
    for text in (
        "posting.html",
        "https://example.com/job",
        "remote",
        "preferred",
        "Fully remote",
        "line 1",
        "Home-working",
        "Uncertainty",
    ):
        assert text in report
    assert "apply/reject" not in report
