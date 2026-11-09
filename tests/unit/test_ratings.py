"""Request-context validation and deterministic arithmetic."""

from decimal import Decimal
from pathlib import Path

import pytest

from job_scan.evidence import assess
from job_scan.models import Assessment, PostingInput, WorkArrangementResult
from job_scan.profiles import Profile, ProfileInput
from job_scan.rating_models import FitResponse
from job_scan.ratings import assemble
from tests.conftest import fictional_profile, fixed_rating


def inputs() -> tuple[PostingInput, ProfileInput]:
    source = PostingInput(
        path=Path("posting.html"),
        html="backend development aaa",
        sha256="source-hash",
        source_url=None,
    )
    return source, ProfileInput(
        path=Path("profile.toml"),
        sha256="profile-hash",
        profile=Profile.model_validate(fictional_profile()),
    )


def work(source: PostingInput) -> Assessment:
    return assess(
        source,
        WorkArrangementResult(
            posting_status="identified",
            posting_explanation=None,
            arrangements=[],
            home_working=[],
            uncertainties=["No work arrangement stated."],
            conflicts=[],
        ),
        "model",
    )


def test_order_weighting_and_evidence() -> None:
    source, profile = inputs()
    results = [
        fixed_rating(name, score)
        for name, score in zip(reversed(profile.profile.dimensions), [20, 40, 60, 80], strict=True)
    ]
    report = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": results}), []
    )
    assert [d.dimension_id for d in report.dimensions] == list(profile.profile.dimensions)
    assert report.overall.value == Decimal(50)
    assert report.overall.numerator == 200
    assert report.overall.denominator == 4
    assert len(report.dimensions[0].evidence) == 1
    assert report.decisive.code == "no_exception_applies"


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "unknown", "excerpt", "evidence", "occurrence"]
)
def test_bad_context(change: str) -> None:
    source, profile = inputs()
    results = [fixed_rating(name) for name in profile.profile.dimensions]
    if change == "missing":
        results.pop()
    elif change == "duplicate":
        results.append(results[0])
    elif change == "unknown":
        results[0]["dimension_id"] = "unknown"
    elif change == "excerpt":
        results[0]["judgments"][0]["preference_quote"] = "unrequested"
    elif change == "evidence":
        results[0]["findings"][0]["evidence"][0]["quote"] = "not present"
    else:
        results[0]["findings"][0]["evidence"][0]["occurrence"] = 2
    with pytest.raises(ValueError):
        assemble(work(source), profile, FitResponse.model_validate({"dimensions": results}), [])


@pytest.mark.parametrize("rated", [0, 1, 2])
def test_partial_unavailable_and_not_configured(rated: int) -> None:
    source, profile = inputs()
    profile.profile.dimensions["field_interest"].preferences = ""
    profile.profile.dimensions["company_affinity"].preferences = " "
    profile.profile.dimensions["technology_fit"].importance = 3
    results = [fixed_rating("role_fit"), fixed_rating("technology_fit", 60)]
    for result in results[rated:]:
        result.update(
            status="insufficient_evidence", score=None, uncertainties=["Missing context."]
        )
    report = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": results}), []
    )
    assert report.overall.status == ["unavailable", "partial", "available"][rated]
    assert report.overall.rated_dimension_count == rated
    assert report.overall.configured_dimension_count == 2
    assert report.overall.total_configured_importance == 4
    assert report.overall.value == [None, Decimal(80), Decimal(65)][rated]
    assert report.dimensions[-1].status == "not_configured"
    assert report.dimensions[-1].score is None
    assert report.dimensions[-1].findings == []


def test_overlap_and_deduplication() -> None:
    source, profile = inputs()
    results = [fixed_rating(name) for name in profile.profile.dimensions]
    quote = {"quote": "aa", "occurrence": 1}
    results[0]["findings"][0]["evidence"] = [quote, quote]
    report = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": results}), []
    )
    assert len(report.dimensions[0].evidence) == 1
    assert report.dimensions[0].evidence[0].start == source.html.index("aaa") + 1


def test_weighting_and_rounding() -> None:
    from job_scan.report import one_decimal

    source, profile = inputs()
    results = [
        fixed_rating(name, score)
        for name, score in zip(profile.profile.dimensions, [80, 95, 10, 50], strict=True)
    ]
    fits = FitResponse.model_validate({"dimensions": results})
    values = []
    for weights in [(1, 1, 1, 1), (1, 5, 1, 1), (1, 1, 5, 1), (5, 1, 1, 1)]:
        for dimension, weight in zip(profile.profile.dimensions.values(), weights, strict=True):
            dimension.importance = weight
        overall = assemble(work(source), profile, fits, []).overall
        numerator = sum(w * s for w, s in zip(weights, [80, 95, 10, 50], strict=True))
        assert overall.numerator == numerator
        assert overall.denominator == sum(weights)
        assert overall.value == Decimal(numerator) / sum(weights)
        assert overall.value is not None
        values.append(overall.value)
    assert values[1] > values[0] > values[2]
    assert values[3] >= values[0]
    assert one_decimal(Decimal("50.05")) == "50.1"
    assert one_decimal(Decimal("50.04")) == "50.0"
    profile.profile.dimensions["company_affinity"].preferences = ""
    results = [fixed_rating(name, 1) for name in list(profile.profile.dimensions)[:-1]]
    for d in profile.profile.dimensions.values():
        d.importance = 1
    overall = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": results}), []
    ).overall
    assert sum(c.value for c in overall.contributions) != Decimal("0.9")
    assert [one_decimal(c.value) for c in overall.contributions] == ["0.3"] * 3
    assert overall.value is not None
    assert one_decimal(overall.value) == "1.0"


@pytest.mark.parametrize("rated", [False, True])
def test_supported_partial_preferences(rated: bool) -> None:
    source, profile = inputs()
    for name, dimension in profile.profile.dimensions.items():
        dimension.preferences = (
            ""
            if name != "role_fit"
            else (
                "I want backend development; mentoring is optional."
                if rated
                else "I want backend development only if there are no management duties."
            )
        )
    result = fixed_rating()
    result["uncertainties"] = [
        "Mentoring is unknown." if rated else "Management duties are unknown."
    ]
    result["explanation"] = (
        "The main backend responsibility supports a rating despite "
        "optional mentoring remaining unknown."
        if rated
        else "The required absence of management duties is unknown; no rating is justified."
    )
    if not rated:
        result.update(status="insufficient_evidence", score=None)
    report = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": [result]}), []
    )
    assert report.dimensions[0].findings
    assert report.dimensions[0].score == (80 if rated else None)
    assert report.overall.status == ("available" if rated else "unavailable")


def test_conflicting_evidence_even_when_unrated() -> None:
    source, profile = inputs()
    source.html = "backend development aaa management duties"
    results = [fixed_rating(name) for name in profile.profile.dimensions]
    results[0].update(
        status="insufficient_evidence",
        score=None,
        uncertainties=[],
        conflicts=[
            {
                "explanation": "Responsibility statements conflict.",
                "evidence": [
                    {"quote": "backend development", "occurrence": 0},
                    {"quote": "management duties", "occurrence": 0},
                ],
            }
        ],
    )
    report = assemble(
        work(source), profile, FitResponse.model_validate({"dimensions": results}), []
    )
    assert report.overall.status == "partial"
    assert report.overall.missing_dimension_ids == ["role_fit"]
    results[0]["conflicts"][0]["evidence"][1]["quote"] = "invented"
    with pytest.raises(ValueError):
        assemble(work(source), profile, FitResponse.model_validate({"dimensions": results}), [])


def test_not_configured_result_is_extra() -> None:
    source, profile = inputs()
    profile.profile.dimensions["role_fit"].preferences = " "
    fits = FitResponse.model_validate(
        {"dimensions": [fixed_rating(name) for name in profile.profile.dimensions]}
    )
    with pytest.raises(ValueError):
        assemble(work(source), profile, fits, [])
