"""Strict model responses and locally derived personalized outcomes."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from job_scan.models import Assessment, Conflict, Evidence, Model, ResolvedEvidence, Text
from job_scan.profiles import ExceptionDeclaration, ProfileInput


class SourceFinding(Model):
    id: Text
    statement: Text
    evidence: Annotated[list[Evidence], Field(min_length=1)]


class PreferenceJudgment(Model):
    preference_quote: Text
    finding_ids: Annotated[list[Text], Field(min_length=1)]
    polarity: Literal["match", "mismatch", "mixed"]
    explanation: Text


class DimensionFit(Model):
    dimension_id: Text
    status: Literal["rated", "insufficient_evidence"]
    score: Annotated[int, Field(ge=0, le=100)] | None
    explanation: Text
    findings: list[SourceFinding]
    judgments: list[PreferenceJudgment]
    uncertainties: list[Text]
    conflicts: list[Conflict]

    @model_validator(mode="after")
    def check_fit(self) -> Self:
        ids = [finding.id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("Finding IDs must be unique within a dimension.")
        if any(not set(j.finding_ids) <= set(ids) for j in self.judgments):
            raise ValueError("Judgments must reference findings in their dimension.")
        if self.status == "rated":
            if self.score is None or not self.findings or not self.judgments:
                raise ValueError("Rated dimensions require score, findings and judgments.")
        elif self.score is not None or not (self.uncertainties or self.conflicts):
            raise ValueError(
                "Insufficient evidence requires null score and uncertainty or conflict."
            )
        return self


class FitResponse(Model):
    dimensions: list[DimensionFit]


class ExceptionMatch(Model):
    exception_id: Text
    status: Literal["matched", "not_matched", "unresolved"]
    explanation: Text
    evidence: list[Evidence]

    @model_validator(mode="after")
    def check_evidence(self) -> Self:
        if self.status != "unresolved" and not self.evidence:
            raise ValueError("Resolved exception claims require source evidence.")
        return self


class ExceptionResponse(Model):
    exceptions: list[ExceptionMatch]


class EvaluatedException(Model):
    declaration: ExceptionDeclaration
    match: ExceptionMatch
    evidence: list[ResolvedEvidence]


class DimensionOutcome(Model):
    dimension_id: str
    importance: Annotated[int, Field(ge=1, le=5)]
    status: Literal["rated", "insufficient_evidence", "not_configured"]
    score: Annotated[int, Field(ge=0, le=100)] | None
    explanation: Text
    findings: list[SourceFinding]
    judgments: list[PreferenceJudgment]
    uncertainties: list[str]
    conflicts: list[Conflict]
    evidence: list[ResolvedEvidence]
    exceptions: list[EvaluatedException]

    @model_validator(mode="after")
    def check_not_configured(self) -> Self:
        if self.status == "not_configured" and (
            self.score is not None
            or self.findings
            or self.judgments
            or self.uncertainties
            or self.conflicts
            or self.evidence
            or self.exceptions
        ):
            raise ValueError("Not-configured dimensions cannot have computed results.")
        if (self.status == "rated") != (self.score is not None):
            raise ValueError("Only rated dimensions have scores.")
        return self


class Contribution(Model):
    dimension_id: str
    importance: int
    score: int
    numerator: int
    value: Decimal


class WeightedOverall(Model):
    status: Literal["available", "partial", "unavailable"]
    numerator: int | None
    denominator: int | None
    value: Decimal | None
    missing_dimension_ids: list[str]
    rated_dimension_count: int
    configured_dimension_count: int
    rated_importance: int
    total_configured_importance: int
    contributions: list[Contribution]


DecisiveCode = Literal[
    "conflicting_exceptions",
    "worth_pursuing_despite_weaknesses",
    "deal_breaker",
    "unresolved_exceptions",
    "no_exception_applies",
]


class DecisiveOutcome(Model):
    code: DecisiveCode
    matched_ids: list[str]
    unresolved_ids: list[str]
    exceptions: list[EvaluatedException]


class PassMetadata(Model):
    stage: Literal["work_arrangement", "fit", "exceptions"]
    requested_model: str
    returned_model: str | None
    reasoning: Literal["low"] = "low"


class PersonalizedAssessment(Model):
    work_arrangement: Assessment
    profile: ProfileInput
    dimensions: list[DimensionOutcome]
    overall: WeightedOverall
    decisive: DecisiveOutcome
    passes: list[PassMetadata]
