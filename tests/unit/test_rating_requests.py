"""Ordinary scoring input excludes weights, declarations and local provenance."""

import copy
import json

from job_scan.ai import fit_request_body
from job_scan.profiles import Profile, fit_projection
from tests.conftest import fictional_profile


def test_projection_and_request_identity() -> None:
    data = fictional_profile()
    data["dimensions"]["technology_fit"]["preferences"] = " "
    data["dimensions"]["role_fit"]["preferences"] = "I want backend development.\n"
    profile = Profile.model_validate(data)
    projection = fit_projection("<h1>Original HTML</h1>", profile)
    assert projection == {
        "html": "<h1>Original HTML</h1>",
        "dimensions": [
            {"dimension_id": name, "preferences": profile.dimensions[name].preferences}
            for name in ["role_fit", "field_interest", "company_affinity"]
        ],
    }
    body = json.loads(json.dumps(fit_request_body("<h1>Original HTML</h1>", profile, "chosen")))
    assert body["store"] is False
    assert json.loads(body["input"][0]["content"]) == projection
    assert body["text"]["format"]["strict"] is True
    changed = copy.deepcopy(data)
    changed["dimensions"]["role_fit"]["importance"] = 5
    changed["dimensions"]["role_fit"]["exceptions"] = [
        {"id": "x", "kind": "deal_breaker", "preference_quote": "backend development"}
    ]
    assert (
        fit_request_body("<h1>Original HTML</h1>", Profile.model_validate(changed), "chosen")
        == body
    )
    assert "technology" not in body["instructions"].lower()
    assert "responsibilit" in body["instructions"].lower()


def test_exception_projection_and_weight_edits() -> None:
    from job_scan.ai import exception_request_body
    from job_scan.profiles import exception_projection

    data = fictional_profile()
    data["dimensions"]["role_fit"]["exceptions"] = [
        {"id": "x", "kind": "deal_breaker", "preference_quote": "backend development"}
    ]
    profile = Profile.model_validate(data)
    fit = fit_request_body("HTML", profile, "model")
    exception = exception_request_body("HTML", profile, "model")
    assert exception_projection("HTML", profile) == {
        "html": "HTML",
        "exceptions": [
            {
                "dimension_id": "role_fit",
                "exception_id": "x",
                "kind": "deal_breaker",
                "preference_quote": "backend development",
            }
        ],
    }
    for weight in range(1, 6):
        for name in profile.dimensions:
            profile.dimensions[name].importance = weight
        assert fit_request_body("HTML", profile, "model") == fit
        assert exception_request_body("HTML", profile, "model") == exception
    profile.dimensions["role_fit"].exceptions[0].kind = "compelling_attraction"
    assert fit_request_body("HTML", profile, "model") == fit
    assert exception_request_body("HTML", profile, "model") != exception
    profile.dimensions["role_fit"].exceptions = []
    assert fit_request_body("HTML", profile, "model") == fit
    profile.dimensions["role_fit"].preferences = " "
    assert fit_request_body("HTML", profile, "model") != fit
