"""Model-local contracts; request-context checks live in assembly tests."""

import pytest
from pydantic import ValidationError

from job_scan.rating_models import DimensionFit, ExceptionMatch, FitResponse
from tests.conftest import fixed_rating


def test_valid_schema() -> None:
    result = DimensionFit.model_validate(fixed_rating())
    assert result.score == 80
    schema = FitResponse.model_json_schema()
    assert schema["additionalProperties"] is False
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


@pytest.mark.parametrize("score", [True, 1.5, "50", -1, 101, None])
def test_invalid_score(score: object) -> None:
    data = fixed_rating()
    data["score"] = score
    with pytest.raises(ValidationError):
        DimensionFit.model_validate(data)


@pytest.mark.parametrize(
    "field", ["score", "explanation", "findings", "judgments", "uncertainties", "conflicts"]
)
def test_required_fields(field: str) -> None:
    data = fixed_rating()
    del data[field]
    with pytest.raises(ValidationError):
        DimensionFit.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        "blank",
        "no-findings",
        "no-judgments",
        "duplicate-findings",
        "no-evidence",
        "no-references",
        "unknown-reference",
        "weight",
        "outcome",
        "not-configured",
    ],
)
def test_invalid_rated_shapes(change: str) -> None:
    data = fixed_rating()
    if change == "blank":
        data["explanation"] = " "
    elif change == "no-findings":
        data["findings"] = []
    elif change == "no-judgments":
        data["judgments"] = []
    elif change == "duplicate-findings":
        data["findings"] *= 2
    elif change == "no-evidence":
        data["findings"][0]["evidence"] = []
    elif change == "no-references":
        data["judgments"][0]["finding_ids"] = []
    elif change == "unknown-reference":
        data["judgments"][0]["finding_ids"] = ["unknown"]
    elif change == "weight":
        data["importance"] = 3
    elif change == "outcome":
        data["outcome"] = "deal_breaker"
    else:
        data["status"] = "not_configured"
    with pytest.raises(ValidationError):
        DimensionFit.model_validate(data)


def test_insufficient_shape() -> None:
    data = fixed_rating()
    data.update(status="insufficient_evidence", score=None)
    with pytest.raises(ValidationError):
        DimensionFit.model_validate(data)
    data["uncertainties"] = ["Management duties are not stated."]
    assert DimensionFit.model_validate(data).score is None
    data["score"] = 50
    with pytest.raises(ValidationError):
        DimensionFit.model_validate(data)


@pytest.mark.parametrize("status", ["matched", "not_matched", "unresolved"])
def test_exception_shape(status: str) -> None:
    data = {
        "exception_id": "x",
        "status": status,
        "explanation": "Source is silent.",
        "evidence": [],
    }
    if status == "unresolved":
        assert ExceptionMatch.model_validate(data).status == "unresolved"
    else:
        with pytest.raises(ValidationError):
            ExceptionMatch.model_validate(data)
    data["evidence"] = [{"quote": "source", "occurrence": 0}]
    ExceptionMatch.model_validate(data)
    for key in ["kind", "importance", "outcome"]:
        with pytest.raises(ValidationError):
            ExceptionMatch.model_validate({**data, key: "forbidden"})


def test_local_not_configured_invariant() -> None:
    from job_scan.rating_models import DimensionOutcome

    data = {
        "dimension_id": "role_fit",
        "importance": 1,
        "status": "not_configured",
        "score": None,
        "explanation": "No preferences configured.",
        "findings": [],
        "judgments": [],
        "uncertainties": [],
        "conflicts": [],
        "evidence": [],
        "exceptions": [],
    }
    DimensionOutcome.model_validate(data)
    for key, value in [
        ("score", 50),
        ("uncertainties", ["Should not compute unknowns for skipped prose."]),
        ("importance", True),
    ]:
        with pytest.raises(ValueError):
            DimensionOutcome.model_validate({**data, key: value})
