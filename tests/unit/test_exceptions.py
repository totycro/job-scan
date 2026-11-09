"""Exceptional status is locally reduced and never changes numeric scoring."""

import pytest

from job_scan.profiles import ExceptionDeclaration
from job_scan.rating_models import ExceptionResponse, FitResponse
from job_scan.ratings import assemble
from tests.conftest import fixed_rating
from tests.unit.test_ratings import inputs, work


@pytest.mark.parametrize(
    "statuses,expected",
    [
        (["not_matched", "not_matched"], "no_exception_applies"),
        (["matched", "not_matched"], "worth_pursuing_despite_weaknesses"),
        (["not_matched", "matched"], "deal_breaker"),
        (["matched", "matched"], "conflicting_exceptions"),
        (["unresolved", "not_matched"], "unresolved_exceptions"),
        (["unresolved", "matched"], "deal_breaker"),
        (["matched", "unresolved"], "worth_pursuing_despite_weaknesses"),
        (["unresolved", "unresolved"], "unresolved_exceptions"),
    ],
)
@pytest.mark.parametrize("same_dimension", [False, True])
def test_outcome_table(statuses: list[str], expected: str, same_dimension: bool) -> None:
    source, profile = inputs()
    fits = FitResponse.model_validate(
        {"dimensions": [fixed_rating(name) for name in profile.profile.dimensions]}
    )
    original = assemble(work(source), profile, fits, []).overall
    for index, kind in enumerate(["compelling_attraction", "deal_breaker"]):
        name = "role_fit" if same_dimension or index == 0 else "technology_fit"
        profile.profile.dimensions[name].exceptions.append(
            ExceptionDeclaration.model_validate(
                {"id": f"x{index}", "kind": kind, "preference_quote": "backend development"}
            )
        )
    exceptions = ExceptionResponse.model_validate(
        {
            "exceptions": [
                {
                    "exception_id": f"x{i}",
                    "status": status,
                    "explanation": "Evidence supports this condition.",
                    "evidence": []
                    if status == "unresolved"
                    else [{"quote": "backend development", "occurrence": 0}],
                }
                for i, status in enumerate(statuses)
            ]
        }
    )
    report = assemble(work(source), profile, fits, [], exceptions)
    assert report.overall == original
    assert report.decisive.code == expected
    from job_scan.report import render_personalized

    text = render_personalized(report)
    labels = {
        "deal_breaker": "deal-breaker",
        "no_exception_applies": "no exceptional preference applies",
    }
    assert labels.get(expected, expected.replace("_", " ")) in text
    assert report.decisive.matched_ids == [
        f"x{i}" for i, s in enumerate(statuses) if s == "matched"
    ]
    assert report.decisive.unresolved_ids == [
        f"x{i}" for i, s in enumerate(statuses) if s == "unresolved"
    ]


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "unknown", "invalid-evidence", "unresolved-evidence"]
)
def test_exception_context(change: str) -> None:
    source, profile = inputs()
    profile.profile.dimensions["role_fit"].exceptions.append(
        ExceptionDeclaration(id="x", kind="deal_breaker", preference_quote="backend development")
    )
    fits = FitResponse.model_validate(
        {"dimensions": [fixed_rating(name) for name in profile.profile.dimensions]}
    )
    result = {
        "exception_id": "x",
        "status": "matched",
        "explanation": "Evidence supports the condition.",
        "evidence": [{"quote": "backend development", "occurrence": 0}],
    }
    results = [result]
    if change == "missing":
        results = []
    elif change == "duplicate":
        results.append(result)
    elif change == "unknown":
        result["exception_id"] = "unknown"
    else:
        result["evidence"] = [{"quote": "absent", "occurrence": 0}]
        if change == "unresolved-evidence":
            result["status"] = "unresolved"
    with pytest.raises(ValueError):
        assemble(
            work(source),
            profile,
            fits,
            [],
            ExceptionResponse.model_validate({"exceptions": results}),
        )
    with pytest.raises(ValueError):
        assemble(work(source), profile, fits, [])
