"""Strict source findings; no I/O or criterion-specific fit policy."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Kind = Literal["remote", "hybrid", "onsite"]


class Model(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class PostingInput(Model):
    path: Path | None
    source_url: str | None
    final_url: str | None = None
    frame_urls: list[str] = Field(default_factory=list)
    html: str
    sha256: str


class Evidence(Model):
    quote: Annotated[str, Field(min_length=1)]
    occurrence: Annotated[int, Field(ge=0)]


class Arrangement(Model):
    kind: Kind
    context: Text
    evidence: Annotated[list[Evidence], Field(min_length=1)]


class Schedule(Model):
    days_text: Text | None = Field(
        description="Exact quantity/range, modifiers and day units only; exclude frequency/period."
    )
    period: Text | None = Field(
        description="Exact complete frequency phrase, including words such as per or each; "
        "do not reduce it to a bare unit or repeat it in days_text."
    )
    kind: Literal["allowed", "expected", "unspecified"]
    context: Text
    evidence: list[Evidence]

    @model_validator(mode="after")
    def check_schedule(self) -> Self:
        if self.kind == "unspecified":
            if self.days_text is not None or self.period is not None:
                raise ValueError("Unspecified schedule must have null quantity and period.")
        elif not self.evidence:
            raise ValueError("Stated schedules require source evidence.")
        return self


class Conflict(Model):
    explanation: Text
    evidence: Annotated[list[Evidence], Field(min_length=2)]


class WorkArrangementResult(Model):
    posting_status: Literal["identified", "ambiguous", "absent"]
    posting_explanation: Text | None
    arrangements: list[Arrangement]
    home_working: list[Schedule]
    uncertainties: list[Text]
    conflicts: list[Conflict]

    @model_validator(mode="after")
    def check_explanation(self) -> Self:
        if (self.posting_status == "identified") != (self.posting_explanation is None):
            raise ValueError("Posting explanation is required only for ambiguous/absent postings.")
        if self.posting_status == "identified" and not self.arrangements and not self.uncertainties:
            raise ValueError("Missing arrangement requires an uncertainty explanation.")
        return self


class ResolvedEvidence(Evidence):
    start: int
    end: int
    line: int
    end_line: int


class Assessment(Model):
    source: PostingInput
    findings: WorkArrangementResult
    evidence: list[ResolvedEvidence]
    fit: list[str]
    model: str
