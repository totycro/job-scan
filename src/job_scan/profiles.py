"""Pure, strict profile parsing. Profile values never enter error messages."""

import tomllib
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, model_validator

from job_scan.criteria import DIMENSIONS
from job_scan.models import Model, Text

DIMENSION_IDS = tuple(d.id for d in DIMENSIONS)
ExceptionKind = Literal["compelling_attraction", "deal_breaker"]


class ExceptionDeclaration(Model):
    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
    kind: ExceptionKind
    preference_quote: Text


class DimensionProfile(Model):
    importance: Annotated[int, Field(ge=1, le=5)]
    preferences: str = ""
    exceptions: list[ExceptionDeclaration] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_declarations(self) -> Self:
        seen: set[tuple[str, str]] = set()
        for item in self.exceptions:
            if item.preference_quote not in self.preferences:
                raise ValueError("Exception excerpt must occur in dimension preferences.")
            key = (item.kind, item.preference_quote)
            if key in seen:
                raise ValueError("Duplicate exception kind and excerpt.")
            seen.add(key)
        return self


class Profile(Model):
    schema_version: Annotated[int, Field(ge=1, le=1)]
    dimensions: dict[str, DimensionProfile]

    @model_validator(mode="after")
    def check_dimensions(self) -> Self:
        if set(self.dimensions) != set(DIMENSION_IDS):
            raise ValueError("Exactly the four supported dimensions are required.")
        if not any(d.preferences.strip() for d in self.dimensions.values()):
            raise ValueError("At least one dimension requires nonblank preferences.")
        ids = [item.id for d in self.dimensions.values() for item in d.exceptions]
        if len(ids) != len(set(ids)):
            raise ValueError("Exception IDs must be unique across the profile.")
        return self


class ProfileInput(Model):
    path: Path
    sha256: str
    profile: Profile


class ProfileError(ValueError):
    """Safe local profile diagnostic, without rejected values or TOML text."""


def parse_profile(text: str) -> Profile:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(
            f"Profile TOML is invalid at line {exc.lineno}, column {exc.colno}."
        ) from None
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        # Unknown keys are user content too: disclose only schema-owned field names.
        allowed = {
            "schema_version",
            "dimensions",
            *DIMENSION_IDS,
            "importance",
            "preferences",
            "exceptions",
            "id",
            "kind",
            "preference_quote",
        }
        errors = []
        for error in exc.errors(include_input=False, include_context=False):
            path = (
                ".".join(
                    str(p) if isinstance(p, int) or p in allowed else "<unknown>"
                    for p in error["loc"]
                )
                or "root"
            )
            reason = error["msg"] if error["type"] == "value_error" else error["type"]
            errors.append(f"{path}: {reason}")
        raise ProfileError("Profile validation failed: " + "; ".join(errors)) from None


def fit_projection(html: str, profile: Profile) -> dict[str, object]:
    return {
        "html": html,
        "dimensions": [
            {"dimension_id": d.id, "preferences": profile.dimensions[d.id].preferences}
            for d in DIMENSIONS
            if profile.dimensions[d.id].preferences.strip()
        ],
    }


def exception_projection(html: str, profile: Profile) -> dict[str, object]:
    return {
        "html": html,
        "exceptions": [
            {
                "dimension_id": d.id,
                "exception_id": item.id,
                "kind": item.kind,
                "preference_quote": item.preference_quote,
            }
            for d in DIMENSIONS
            for item in profile.dimensions[d.id].exceptions
        ],
    }


def has_exceptions(profile: Profile) -> bool:
    return any(d.exceptions for d in profile.dimensions.values())
