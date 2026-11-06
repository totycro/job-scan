import copy

import pytest
from pydantic import ValidationError

from job_scan.models import Evidence, WorkArrangementResult


def test_valid_and_strict(remote_result: dict[str, object]) -> None:
    result = WorkArrangementResult.model_validate(remote_result)
    assert result.arrangements[0].kind == "remote"
    for patch in ({"extra": 1}, {"posting_status": "unknown"}, {"posting_explanation": "why"}):
        with pytest.raises(ValidationError):
            WorkArrangementResult.model_validate(remote_result | patch)
    for quote, occurrence in (("", 0), ("x", -1), ("x", "0"), ("x", True)):
        with pytest.raises(ValidationError):
            Evidence.model_validate({"quote": quote, "occurrence": occurrence})


def test_failure_explanation(remote_result: dict[str, object]) -> None:
    for status in ("ambiguous", "absent"):
        for explanation in (None, "", "   "):
            with pytest.raises(ValidationError):
                WorkArrangementResult.model_validate(
                    remote_result
                    | {
                        "posting_status": status,
                        "posting_explanation": explanation,
                    }
                )
        assert (
            WorkArrangementResult.model_validate(
                remote_result
                | {
                    "posting_status": status,
                    "posting_explanation": "No target role",
                }
            ).posting_explanation
            is not None
        )


def test_evidence_and_schedule(remote_result: dict[str, object]) -> None:
    data = copy.deepcopy(remote_result)
    data["arrangements"] = [{"kind": "hybrid", "context": "x", "evidence": []}]
    with pytest.raises(ValidationError):
        WorkArrangementResult.model_validate(data)
    data["arrangements"] = []
    data["uncertainties"] = ["Arrangement not stated"]
    base = {
        "kind": "unspecified",
        "days_text": None,
        "period": None,
        "context": "Not stated",
        "evidence": [],
    }
    data["home_working"] = [base]
    assert WorkArrangementResult.model_validate(data).home_working
    for patch in ({"days_text": "2"}, {"kind": "allowed"}):
        data["home_working"] = [base | patch]
        with pytest.raises(ValidationError):
            WorkArrangementResult.model_validate(data)
    data["home_working"] = [
        base
        | {"kind": "expected", "evidence": [{"quote": "Home working is expected", "occurrence": 0}]}
    ]
    assert WorkArrangementResult.model_validate(data).home_working[0].days_text is None
    data["conflicts"] = [{"explanation": "Conflicting", "evidence": []}]
    with pytest.raises(ValidationError):
        WorkArrangementResult.model_validate(data)


def test_missing_details_need_uncertainty(remote_result: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="uncertainty"):
        WorkArrangementResult.model_validate(remote_result | {"arrangements": []})
    assert (
        WorkArrangementResult.model_validate(
            remote_result | {"arrangements": [], "uncertainties": ["Arrangement is not stated."]}
        ).arrangements
        == []
    )
