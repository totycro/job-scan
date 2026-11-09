"""Profile contract: strict types, exact dimensions, and safe diagnostics."""

import copy
from pathlib import Path

import pytest

from job_scan.profiles import Profile, ProfileError, parse_profile
from tests.conftest import fictional_profile

EXAMPLE = Path("specs/002-personalized-job-ratings/contracts/profile.example.toml")


def test_example_and_defaults() -> None:
    profile = parse_profile(EXAMPLE.read_text())
    assert profile.dimensions["technology_fit"].importance == 4
    assert len(profile.dimensions["technology_fit"].exceptions) == 1
    data = fictional_profile()
    dimensions = data["dimensions"]
    assert isinstance(dimensions, dict)
    dimensions["technology_fit"] = {"importance": 5}
    dimensions["field_interest"] = {"importance": 1, "preferences": " \n"}
    profile = Profile.model_validate(data)
    assert profile.dimensions["technology_fit"].preferences == ""
    assert not profile.dimensions["role_fit"].exceptions


@pytest.mark.parametrize("value", [0, 6, -1, True, 1.0, "2", None])
def test_strict_importance(value: object) -> None:
    data = fictional_profile()
    data["dimensions"]["role_fit"]["importance"] = value
    with pytest.raises(ValueError):
        Profile.model_validate(data)


@pytest.mark.parametrize("value", [True, "1", 1.0, 2, None])
def test_strict_version(value: object) -> None:
    data = fictional_profile()
    data["schema_version"] = value
    with pytest.raises(ValueError):
        Profile.model_validate(data)


@pytest.mark.parametrize("change", ["missing", "unknown", "extra", "blank", "type", "no-weight"])
def test_invalid_structure(change: str) -> None:
    data = fictional_profile()
    dimensions = data["dimensions"]
    if change == "missing":
        del dimensions["role_fit"]
    elif change == "unknown":
        dimensions["unknown"] = dimensions.pop("role_fit")
    elif change == "extra":
        data["private_field"] = "PRIVATE-VALUE"
    elif change == "blank":
        for dimension in dimensions.values():
            dimension["preferences"] = " "
    elif change == "type":
        dimensions["role_fit"]["preferences"] = 42
    else:
        del dimensions["role_fit"]["importance"]
    with pytest.raises(ValueError):
        Profile.model_validate(data)


def declaration() -> dict[str, str]:
    return {"id": "backend", "kind": "deal_breaker", "preference_quote": "backend development"}


@pytest.mark.parametrize(
    "change",
    [
        "id",
        "long-id",
        "kind",
        "quote",
        "blank",
        "extra",
        "duplicate-id",
        "duplicate-condition",
        "no-preferences",
    ],
)
def test_invalid_declarations(change: str) -> None:
    data = fictional_profile()
    role = data["dimensions"]["role_fit"]
    item = declaration()
    role["exceptions"] = [item]
    if change == "id":
        item["id"] = "Invalid!"
    elif change == "long-id":
        item["id"] = "x" * 65
    elif change == "kind":
        item["kind"] = "bonus"
    elif change == "quote":
        item["preference_quote"] = "missing secret"
    elif change == "blank":
        item["preference_quote"] = " "
    elif change == "extra":
        item["weight"] = "5"
    elif change == "duplicate-id":
        data["dimensions"]["technology_fit"]["exceptions"] = [copy.copy(item)]
    elif change == "duplicate-condition":
        role["exceptions"].append({**item, "id": "another"})
    else:
        del role["preferences"]
    with pytest.raises(ValueError):
        Profile.model_validate(data)


def test_opposite_conditions_allowed_and_no_mutation() -> None:
    data = fictional_profile()
    data["dimensions"]["role_fit"]["exceptions"] = [
        declaration(),
        {**declaration(), "id": "other", "kind": "compelling_attraction"},
    ]
    original = copy.deepcopy(data)
    Profile.model_validate(data)
    assert data == original


@pytest.mark.parametrize(
    "text",
    [
        "schema_version = 1\nschema_version = 1",
        "[dimensions.role_fit]\n[dimensions.role_fit]",
        "PRIVATE-VALUE = [",
        'schema_version = "PRIVATE-VALUE"',
    ],
)
def test_safe_parse_failure(text: str) -> None:
    with pytest.raises(ProfileError) as failure:
        parse_profile(text)
    assert "PRIVATE-VALUE" not in str(failure.value)
    assert "Profile" in str(failure.value)
