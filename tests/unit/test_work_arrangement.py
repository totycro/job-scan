from job_scan.criteria.work_arrangement import INSTRUCTIONS, fit_judgments
from job_scan.models import WorkArrangementResult


def test_preferences(remote_result: dict[str, object]) -> None:
    result = WorkArrangementResult.model_validate(remote_result)
    assert "preferred" in fit_judgments(result)[0]
    result.arrangements[0].kind = "hybrid"
    assert "acceptable" in fit_judgments(result)[0]
    result.arrangements[0].kind = "onsite"
    assert "outside" in fit_judgments(result)[0]
    result.arrangements = []
    assert "uncertain" in fit_judgments(result)[0]
    assert "untrusted" in INSTRUCTIONS
    assert "office days" in INSTRUCTIONS
