"""Keep facts, user excerpts and inferred fit distinct in terminal output."""

from job_scan.rating_models import FitResponse
from job_scan.ratings import assemble
from job_scan.report import render_personalized
from tests.conftest import fixed_rating
from tests.unit.test_ratings import inputs, work


def test_personalized_rendering() -> None:
    source, profile = inputs()
    profile.path = profile.path.with_name("profile\x1b.toml")
    profile.profile.dimensions["company_affinity"].preferences = ""
    results = [fixed_rating(name) for name in list(profile.profile.dimensions)[:-1]]
    text = render_personalized(
        assemble(work(source), profile, FitResponse.model_validate({"dimensions": results}), [])
    )
    for expected in [
        "Work arrangement",
        "Role fit",
        "Technology fit",
        "Field interest",
        "Company affinity",
        "not configured",
        "subjective",
        "80.0/100",
        "240 / 3",
        "Posting fact",
        "Preference excerpt",
        "Inferred fit",
        "no exceptional preference applies",
        "profile�.toml",
        "chars",
    ]:
        assert expected in text
    assert "\x1b" not in text
    assert "schema_version" not in text


def test_exception_rendering_with_unavailable_mean() -> None:
    from job_scan.profiles import ExceptionDeclaration
    from job_scan.rating_models import ExceptionResponse

    source, profile = inputs()
    for i, kind in enumerate(["compelling_attraction", "deal_breaker", "deal_breaker"]):
        profile.profile.dimensions["role_fit"].exceptions.append(
            ExceptionDeclaration.model_validate(
                {"id": f"x{i}", "kind": kind, "preference_quote": "backend development"}
            )
        )
    fits = [fixed_rating(name) for name in profile.profile.dimensions]
    for fit in fits:
        fit.update(
            status="insufficient_evidence", score=None, uncertainties=["Required context missing."]
        )
    exceptions = ExceptionResponse.model_validate(
        {
            "exceptions": [
                {
                    "exception_id": f"x{i}",
                    "status": "unresolved" if i == 2 else "matched",
                    "explanation": "Required condition is evidenced or remains unknown.",
                    "evidence": [{"quote": "backend development", "occurrence": 0}],
                }
                for i in range(3)
            ]
        }
    )
    text = render_personalized(
        assemble(
            work(source), profile, FitResponse.model_validate({"dimensions": fits}), [], exceptions
        )
    )
    for expected in [
        "conflicting exceptions",
        "compelling attraction",
        "deal breaker",
        "unresolved",
        "confirmed matches only",
        "Unavailable",
        "x0",
        "x1",
        "x2",
        "backend development",
    ]:
        assert expected in text
    assert "/100" not in text


def test_partial_mean_discloses_every_missing_reason() -> None:
    source, profile = inputs()
    results = [fixed_rating(name) for name in profile.profile.dimensions]
    for result in results[1:]:
        result.update(
            status="insufficient_evidence",
            score=None,
            explanation=f"Missing context for {result['dimension_id']}.",
            uncertainties=["An unassessed required preference prevents a judgment."],
        )
    text = render_personalized(
        assemble(work(source), profile, FitResponse.model_validate({"dimensions": results}), [])
    )
    for expected in [
        "Partial overall: 80.0/100",
        "80 / 1",
        "Dimensions rated: 1/4",
        "importance coverage: 1/4",
        "Missing Technology fit",
        "Missing Field interest",
        "Missing Company affinity",
        "unassessed required preference",
    ]:
        assert expected in text


def test_per_pass_model_identity_sanitized() -> None:
    from job_scan.rating_models import PassMetadata

    source, profile = inputs()
    fits = FitResponse.model_validate(
        {"dimensions": [fixed_rating(name) for name in profile.profile.dimensions]}
    )
    report = assemble(
        work(source),
        profile,
        fits,
        [
            PassMetadata(stage="work_arrangement", requested_model="chosen", returned_model=None),
            PassMetadata(stage="fit", requested_model="chosen", returned_model="returned\x1b"),
        ],
    )
    text = render_personalized(report)
    assert "work_arrangement model: requested chosen; returned not reported; reasoning low" in text
    assert "fit model: requested chosen; returned returned�; reasoning low" in text
