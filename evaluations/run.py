"""Opt-in live golden evaluation and bound manual review; never rewrites expectations."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Annotated, Literal, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from job_scan.ai import (
    DEFAULT_MODEL,
    EXCEPTION_PROMPT_VERSION,
    FIT_PROMPT_VERSION,
    Event,
    ResponsesClient,
    exception_request_body,
    fit_request_body,
    request_body,
)
from job_scan.auth import RESOURCE, ChatGPTSession
from job_scan.cli import load_posting, load_profile
from job_scan.criteria.work_arrangement import INSTRUCTIONS, PROMPT_VERSION
from job_scan.evidence import assess, resolve
from job_scan.models import Evidence, Kind, Model, WorkArrangementResult
from job_scan.profiles import DIMENSION_IDS, has_exceptions
from job_scan.rating_models import DecisiveCode, PassMetadata, PersonalizedAssessment
from job_scan.ratings import assemble, build_dimensions
from job_scan.report import render, render_personalized

ROOT = Path(__file__).resolve().parent


class ExpectedSchedule(Model):
    status: Literal["not_stated", "stated"] | None = None
    kind: Literal["allowed", "expected", "unspecified"] | None = None
    days_text: str | None = None
    period: str | None = None


class Expected(Model):
    arrangement: Kind | list[Kind] | None = None
    home_working_schedule: ExpectedSchedule | None = None
    posting_status: Literal["identified", "ambiguous", "absent"] | None = None


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["approved", "pending_owner_review"]
    expectation_authorship: str
    posting_sha256: str
    expected: Expected
    evidence: list[Evidence]
    required_findings: list[str]
    prohibited_conclusions: list[str]
    owner_note: str | None = None
    review_question: str | None = None


class Golden(BaseModel):
    schema_version: Literal[1]
    case_id: str
    criteria: dict[str, JsonValue]


class Metadata(BaseModel):
    schema_version: Literal[1]
    case_id: str
    content_review_status: Literal["approved", "pending_owner_review"]
    posting_sha256: str


class ManifestEntry(Model):
    id: str
    mode: Literal["work_arrangement", "personalized"]
    posting: str
    profile: str | None
    expectations: str

    @model_validator(mode="after")
    def check_entry(self) -> Self:
        if (self.mode == "personalized") != (self.profile is not None):
            raise ValueError("Only personalized entries require profiles.")
        for value in [self.posting, self.profile, self.expectations]:
            if value is not None and (Path(value).is_absolute() or ".." in Path(value).parts):
                raise ValueError("Manifest paths must stay within evaluations.")
        if not self.id.strip():
            raise ValueError("Case ID must be nonblank.")
        return self


class Manifest(Model):
    schema_version: Annotated[int, Field(ge=2, le=2)]
    required_cases: Annotated[list[ManifestEntry], Field(min_length=1)]

    @model_validator(mode="after")
    def check_ids(self) -> Self:
        ids = [e.id for e in self.required_cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Required pair IDs must be unique.")
        return self


class PersonalizedCriterion(Model):
    state: Literal["rated", "insufficient_evidence", "not_configured"]
    required_findings: list[str]
    prohibited_conclusions: list[str]
    evidence: list[Evidence]
    preference_excerpts: list[str]
    exceptions: dict[str, Literal["matched", "not_matched", "unresolved"]]
    score_band: tuple[int, int] | None
    relative_to: str | None
    direction: Literal["higher", "lower"] | None

    @model_validator(mode="after")
    def check_comparison(self) -> Self:
        if (self.relative_to is None) != (self.direction is None):
            raise ValueError("Relative assertions require pair ID and direction.")
        if self.score_band is not None:
            low, high = self.score_band
            if not 0 <= low <= high <= 100:
                raise ValueError("Score bands must be within 0-100.")
        return self


class ExpectedOverall(Model):
    status: Literal["available", "partial", "unavailable"]
    missing_dimension_ids: list[str]
    rated_dimension_count: int
    configured_dimension_count: int
    rated_importance: int
    total_configured_importance: int


class PersonalizedExpected(Model):
    schema_version: Annotated[int, Field(ge=1, le=1)]
    case_id: str
    posting_sha256: str
    profile_sha256: str
    review_status: Literal["approved", "pending_owner_review"]
    expectation_authorship: str
    criteria: dict[str, PersonalizedCriterion]
    overall: ExpectedOverall
    decisive_code: DecisiveCode

    @model_validator(mode="after")
    def check_ids(self) -> Self:
        if not set(self.criteria) <= set(DIMENSION_IDS):
            raise ValueError("Unknown expected dimension ID.")
        if not set(self.overall.missing_dimension_ids) <= set(DIMENSION_IDS):
            raise ValueError("Unknown missing dimension ID.")
        if not self.expectation_authorship.strip():
            raise ValueError("Expectation authorship is required.")
        return self


class StageResult(PassMetadata):
    seconds: float
    prompt_version: str
    prompt_hash: str
    schema_hash: str
    request_hash: str
    outcome: Literal["completed", "failed"] = "completed"
    result: JsonValue = None


class CaseResult(BaseModel):
    case: str
    criterion: Criterion | None = None
    entry: ManifestEntry | None = None
    profile_hash: str | None = None
    profile_schema_version: int | None = None
    personalized_expected: PersonalizedExpected | None = None
    personalized_result: PersonalizedAssessment | None = None
    stages: list[StageResult] = Field(default_factory=list)
    input_hash: str
    expectation_file_hash: str
    metadata_file_hash: str
    expected_hash: str | None = None
    status: str
    returned_model: str | None = None
    request_hash: str | None = None
    result: WorkArrangementResult | None = None
    report: str | None = None
    explanation: str | None = None


class ManualChecks(Model):
    semantic_findings: bool
    evidence_relevance: bool
    prohibited_conclusions_absent: bool
    report_usable: bool
    notes: str


class ManualReview(Model):
    run_id: str
    reviewer: str
    cases: dict[str, ManualChecks]


class Run(BaseModel):
    timestamp: str
    git_revision: str
    source_hash: str
    model: str
    reasoning: str = "low"
    prompt_version: str = PROMPT_VERSION
    prompt_hash: str
    schema_hash: str
    criterion: str
    cases: list[CaseResult]
    limitations: list[str]
    run_id: str = ""
    review: ManualReview | None = None
    accepted: bool = False
    readiness_issues: list[str] = Field(default_factory=list)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def check_expected(expected: Expected, result: WorkArrangementResult) -> bool:
    if expected.posting_status is not None and expected.posting_status != result.posting_status:
        return False
    if result.posting_status != "identified":
        return expected.posting_status == result.posting_status
    if "arrangement" in expected.model_fields_set:
        value = expected.arrangement
        if value is None:
            raise ValueError("Null arrangement expectation is unsupported; use an empty array.")
        wanted = {value} if isinstance(value, str) else set(value)
        if {a.kind for a in result.arrangements} != wanted:
            return False
    schedule = expected.home_working_schedule
    if schedule is None:
        if "home_working_schedule" in expected.model_fields_set:
            raise ValueError("Null schedule expectation is unsupported; use explicit fields.")
        return True
    schedules = result.home_working
    # Never choose one favorable schedule among several without a context-specific oracle.
    if len(schedules) > 1:
        return False
    finding = schedules[0] if schedules else None
    not_stated = finding is None or finding.kind == "unspecified"
    if schedule.status is not None and (schedule.status == "not_stated") != not_stated:
        return False
    actual = {
        "kind": finding.kind if finding else None,
        "days_text": finding.days_text if finding else None,
        "period": finding.period if finding else None,
    }
    return all(
        actual[k] == getattr(schedule, k) for k in schedule.model_fields_set if k != "status"
    )


def inspect_case(path: Path, criterion: str) -> CaseResult:
    source = load_posting(path / "posting.html")
    contents = (path / "expected.json").read_bytes()
    golden = Golden.model_validate_json(contents)
    metadata = Metadata.model_validate_json((path / "metadata.json").read_bytes())
    selected = (
        Criterion.model_validate(golden.criteria[criterion])
        if criterion in golden.criteria
        else None
    )
    case = CaseResult(
        case=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        criterion=selected,
        input_hash=source.sha256,
        expectation_file_hash=digest(contents),
        metadata_file_hash=digest((path / "metadata.json").read_bytes()),
        status="ready",
    )
    if selected is None:
        case.status = "not_evaluated"
        case.explanation = "Criterion is not annotated."
        return case
    case.expected_hash = selected.posting_sha256
    if source.sha256 != selected.posting_sha256 or source.sha256 != metadata.posting_sha256:
        case.status = "stale"
    elif metadata.content_review_status != "approved" or selected.review_status != "approved":
        case.status = "pending_review"
    for evidence in selected.evidence:
        resolve(source.html, evidence)
    return case


def inspect_entry(entry: ManifestEntry) -> CaseResult:
    if entry.mode == "work_arrangement":
        # The legacy oracle and posting bytes remain unchanged.
        if entry.expectations != str(Path(entry.posting).with_name("expected.json")):
            raise ValueError("Legacy expectations must accompany their posting.")
        case = inspect_case((ROOT / entry.posting).parent, "work_arrangement")
        case.case, case.entry = entry.id, entry
        return case
    source = load_posting(ROOT / entry.posting)
    if entry.profile is None:
        raise ValueError("Personalized profile missing.")
    profile = load_profile(ROOT / entry.profile)
    expected = PersonalizedExpected.model_validate_json((ROOT / entry.expectations).read_bytes())
    metadata_path = (ROOT / entry.posting).with_name("metadata.json")
    metadata = Metadata.model_validate_json(metadata_path.read_bytes())
    # Source metadata belongs to the posting and may be shared by several profile pairs.
    if expected.case_id != entry.id:
        raise ValueError("Pair identity does not match its annotations.")
    if not expected.criteria:
        raise ValueError("Personalized expectations must annotate dimensions.")
    for name, criterion in expected.criteria.items():
        dimension = profile.profile.dimensions[name]
        for evidence in criterion.evidence:
            resolve(source.html, evidence)
        if any(
            not q.strip() or q not in dimension.preferences for q in criterion.preference_excerpts
        ):
            raise ValueError("Expected preference excerpt does not match profile.")
        if not set(criterion.exceptions) <= {e.id for e in dimension.exceptions}:
            raise ValueError("Unknown expected declaration ID.")
        if (criterion.state == "not_configured") == bool(dimension.preferences.strip()):
            raise ValueError("Expected state disagrees with profile configuration.")
    stale = source.sha256 != expected.posting_sha256 or source.sha256 != metadata.posting_sha256
    stale = stale or profile.sha256 != expected.profile_sha256
    pending = metadata.content_review_status != "approved" or expected.review_status != "approved"
    return CaseResult(
        case=entry.id,
        entry=entry,
        input_hash=source.sha256,
        profile_hash=profile.sha256,
        profile_schema_version=profile.profile.schema_version,
        expectation_file_hash=digest((ROOT / entry.expectations).read_bytes()),
        metadata_file_hash=digest(metadata_path.read_bytes()),
        personalized_expected=expected,
        status="stale" if stale else "pending_review" if pending else "ready",
    )


def check_personalized(expected: PersonalizedExpected, result: PersonalizedAssessment) -> bool:
    dimensions = {d.dimension_id: d for d in result.dimensions}
    for name, criterion in expected.criteria.items():
        actual = dimensions[name]
        if actual.status != criterion.state:
            return False
        if criterion.score_band is not None:
            low, high = criterion.score_band
            if actual.score is None or not low <= actual.score <= high:
                return False
        # An expected quote identifies a raw-HTML passage, not the model's quotation boundaries.
        # Narrower/split citations may reference it; owner review still checks relevance/entailment.
        for evidence in criterion.evidence:
            try:
                passage = resolve(result.work_arrangement.source.html, evidence)
            except ValueError:
                return False
            if not any(
                cited.start < passage.end and passage.start < cited.end for cited in actual.evidence
            ):
                return False
        statuses = {e.match.exception_id: e.match.status for e in actual.exceptions}
        if any(statuses.get(key) != value for key, value in criterion.exceptions.items()):
            return False
    overall = result.overall.model_dump()
    return (
        all(overall[key] == value for key, value in expected.overall.model_dump().items())
        and result.decisive.code == expected.decisive_code
    )


def stage_result(
    stage: Literal["work_arrangement", "fit", "exceptions"],
    model: str,
    returned: str | None,
    started: float,
    body: dict[str, object],
    version: str,
) -> StageResult:
    # Serialize exactly as HTTPX does for replay identity.
    request = httpx.Request("POST", RESOURCE + "/responses", json=body)
    payload = json.loads(request.content)
    return StageResult(
        stage=stage,
        requested_model=model,
        returned_model=returned,
        seconds=time.monotonic() - started,
        prompt_version=version,
        prompt_hash=digest(payload["instructions"].encode()),
        schema_hash=digest(
            json.dumps(payload["text"]["format"]["schema"], sort_keys=True).encode()
        ),
        request_hash=digest(request.content),
    )


def evaluate_stage[T: BaseModel](
    case: CaseResult,
    client: ResponsesClient,
    stage: Literal["work_arrangement", "fit", "exceptions"],
    model: str,
    body: dict[str, object],
    version: str,
    action: Callable[[], T],
) -> T:
    started = time.monotonic()
    try:
        result = action()
    except RuntimeError, ValueError, httpx.HTTPError:
        trace = stage_result(stage, model, client.returned_model, started, body, version)
        trace.outcome = "failed"
        case.stages.append(trace)
        raise
    trace = stage_result(stage, model, client.returned_model, started, body, version)
    trace.result = json.loads(result.model_dump_json())
    case.stages.append(trace)
    return result


def source_hash() -> str:
    paths = [
        *(ROOT.parent / "src/job_scan").rglob("*.py"),
        *ROOT.glob("*.py"),
        ROOT.parent / "uv.lock",
        ROOT / "manifest.json",
    ]
    return digest(
        b"".join(str(p.relative_to(ROOT.parent)).encode() + p.read_bytes() for p in sorted(paths))
    )


def run_fingerprint(run: Run) -> str:
    return digest(run.model_dump_json(exclude={"run_id", "review", "accepted"}).encode())


def accept_review(run: Run, review: ManualReview) -> bool:
    if review.run_id != run.run_id or run_fingerprint(run) != run.run_id:
        raise ValueError("Manual review does not match the immutable evaluation run.")
    if run.source_hash != source_hash():
        raise ValueError("Application or evaluation code changed; rerun evaluation.")
    manifest = Manifest.model_validate_json((ROOT / "manifest.json").read_bytes())
    if coverage_issues(manifest):
        raise ValueError("Required acceptance coverage changed; rerun evaluation.")
    expected_ids = {e.id for e in manifest.required_cases}
    actual_ids = [c.case for c in run.cases]
    if (
        len(actual_ids) != len(set(actual_ids))
        or set(actual_ids) != expected_ids
        or set(review.cases) != expected_ids
    ):
        raise ValueError("Run and review must cover exactly the complete required case IDs.")
    entries = {e.id: e for e in manifest.required_cases}
    for case in run.cases:
        entry = entries[case.case]
        if case.entry is not None and case.entry != entry:
            raise ValueError("Manifest entry changed; rerun evaluation.")
        path = ROOT / entry.posting
        if (
            digest(path.read_bytes()) != case.input_hash
            or digest((ROOT / entry.expectations).read_bytes()) != case.expectation_file_hash
            or digest(path.with_name("metadata.json").read_bytes()) != case.metadata_file_hash
            or (
                entry.profile is not None
                and digest((ROOT / entry.profile).read_bytes()) != case.profile_hash
            )
        ):
            raise ValueError(
                "Case content, expectations or content review changed; rerun evaluation."
            )
        if inspect_entry(entry).status != "ready":
            raise ValueError("Current source/expectation review is not ready.")
    run.review = review
    run.accepted = (
        not run.readiness_issues
        and bool(run.cases)
        and all(
            case.status == "automatic_pass"
            and case.case in review.cases
            and all(
                (
                    review.cases[case.case].semantic_findings,
                    review.cases[case.case].evidence_relevance,
                    review.cases[case.case].prohibited_conclusions_absent,
                    review.cases[case.case].report_usable,
                )
            )
            for case in run.cases
        )
    )
    return run.accepted


class Recorder:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def response(self, response: httpx.Response) -> None:
        if str(response.request.url) != RESOURCE + "/responses":
            return
        # Reading here buffers the real response under the inference deadline. Only
        # validated SSE event fields are persisted; never headers or OAuth traffic.
        response.read()
        events = []
        for line in response.text.splitlines():
            if line.startswith("data:") and line[5:].strip() != "[DONE]":
                event = Event.model_validate_json(line[5:])
                events.append(event)
        if not response.is_success or not any(e.type == "response.completed" for e in events):
            return
        sanitized = "".join("data: " + e.model_dump_json() + "\n\n" for e in events)
        request_hash = hashlib.sha256(response.request.content).hexdigest()
        cassette = {
            "provenance": "Sanitized actual-provider SSE for a generic golden fixture; "
            "captured by evaluations/run.py. Never an expected-answer oracle.",
            "input_hash": None,
            "exchanges": [
                {
                    "method": response.request.method,
                    "url": str(response.request.url),
                    "request_sha256": request_hash,
                    "status": response.status_code,
                    "body": sanitized,
                }
            ],
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"actual-{request_hash}.json").write_text(
            json.dumps(cassette, indent=2) + "\n"
        )


# Required acceptance coverage is code-owned; removing a manifest entry cannot waive it.
BASELINE_CASE_IDS = (
    "cases/posting-01",
    "cases/posting-02",
    "cases/posting-03",
    "fixtures/ambiguous",
    "fixtures/conflict",
    "fixtures/flexible",
    "fixtures/hybrid-allowed",
    "fixtures/hybrid-expected",
    "fixtures/loading",
    "fixtures/missing",
    "fixtures/office-days",
    "fixtures/qualitative",
    "fixtures/remote-restrictions",
    "fixtures/structure-pair/allowed",
    "fixtures/structure-pair/expected",
    "fixtures/untrusted-instructions",
)
PERSONALIZED_CASE_IDS = (
    "role-contrast-high",
    "role-contrast-low",
    "technology-contrast-high",
    "technology-contrast-low",
    "field-contrast-high",
    "field-contrast-low",
    "affinity-contrast-high",
    "affinity-contrast-low",
    "attraction-despite-weaknesses",
    "breaker-despite-strengths",
    "ordinary-undeclared",
    "opposing-across-dimensions",
    "opposing-same-dimension",
    "unresolved-only",
    "unresolved-plus-attraction",
    "unresolved-plus-breaker",
    "unresolved-plus-both",
    "unavailable-with-attraction",
    "exception-omitted-unresolved",
    "partial-optional-rated",
    "partial-required-unknown",
    "partial-overall",
    "all-unknown",
    "conflicting-responsibilities",
    "omitted-technology",
    "agency-client-separation",
    "company-name-beliefs",
    "structure-backend",
    "structure-management",
    "untrusted-profile-instructions",
    "exception-explicit-not-matched",
)


def coverage_issues(manifest: Manifest) -> list[str]:
    entries = {e.id: e for e in manifest.required_cases}
    issues = []
    for mode, ids in [
        ("work_arrangement", BASELINE_CASE_IDS),
        ("personalized", PERSONALIZED_CASE_IDS),
    ]:
        for name in ids:
            if name not in entries or entries[name].mode != mode:
                issues.append(f"Missing mandatory {mode} coverage: {name}")
    return issues


def evaluate(manifest: Manifest, model: str, *, live: bool, recordings: Path | None = None) -> Run:
    cases = [inspect_entry(entry) for entry in manifest.required_cases]
    issues = coverage_issues(manifest)
    by_id = {c.case: c for c in cases}
    for case in cases:
        expected = case.personalized_expected
        if expected is None:
            continue
        configured = {
            name
            for name, criterion in expected.criteria.items()
            if criterion.state != "not_configured"
        }
        if case.entry is not None and case.entry.profile is not None:
            profile = load_profile(ROOT / case.entry.profile)
            if configured != {
                name for name, d in profile.profile.dimensions.items() if d.preferences.strip()
            }:
                issues.append(
                    f"Not evaluated: all configured dimensions need annotations for {case.case}"
                )
        for name, criterion in expected.criteria.items():
            if criterion.relative_to is not None:
                other = by_id.get(criterion.relative_to)
                if (
                    other is None
                    or other.personalized_expected is None
                    or name not in other.personalized_expected.criteria
                ):
                    issues.append(f"Invalid comparative pair reference for {case.case}")
    if live and (issues or any(case.status != "ready" for case in cases)):
        raise ValueError("Every required case must be ready before live inference.")
    if live:
        if recordings is not None:
            http = httpx.Client(
                timeout=httpx.Timeout(180, connect=10),
                event_hooks={"response": [Recorder(recordings).response]},
            )
        else:
            http = None
        with ChatGPTSession() as session, ResponsesClient(session, http) as client:
            for case in cases:
                if case.status != "ready":
                    continue
                entry = case.entry
                if entry is None:
                    raise ValueError("Missing manifest entry.")
                source = load_posting(ROOT / entry.posting)
                case.request_hash = digest(
                    json.dumps(request_body(source.html, model), sort_keys=True).encode()
                )
                try:
                    result = evaluate_stage(
                        case,
                        client,
                        "work_arrangement",
                        model,
                        request_body(source.html, model),
                        PROMPT_VERSION,
                        partial(client.assess_html, source.html, model),
                    )
                    case.result = result
                    case.returned_model = client.returned_model
                    if result.posting_status == "identified":
                        case.report = render(assess(source, result, client.returned_model or model))
                    else:
                        case.report = result.posting_explanation
                    if entry.mode == "personalized":
                        if entry.profile is None or case.personalized_expected is None:
                            raise ValueError("Missing personalized context.")
                        profile = load_profile(ROOT / entry.profile)
                        work = assess(source, result, client.returned_model or model)
                        fits = evaluate_stage(
                            case,
                            client,
                            "fit",
                            model,
                            fit_request_body(source.html, profile.profile, model),
                            FIT_PROMPT_VERSION,
                            partial(client.assess_fit, source.html, profile.profile, model),
                        )
                        build_dimensions(work, profile, fits)
                        exceptions = None
                        if has_exceptions(profile.profile):
                            exceptions = evaluate_stage(
                                case,
                                client,
                                "exceptions",
                                model,
                                exception_request_body(source.html, profile.profile, model),
                                EXCEPTION_PROMPT_VERSION,
                                partial(
                                    client.assess_exceptions, source.html, profile.profile, model
                                ),
                            )
                        case.personalized_result = assemble(
                            work,
                            profile,
                            fits,
                            [
                                PassMetadata.model_validate(
                                    s.model_dump(
                                        include={
                                            "stage",
                                            "requested_model",
                                            "returned_model",
                                            "reasoning",
                                        }
                                    )
                                )
                                for s in case.stages
                            ],
                            exceptions,
                        )
                        case.report = render_personalized(case.personalized_result)
                        case.status = (
                            "automatic_pass"
                            if check_personalized(
                                case.personalized_expected, case.personalized_result
                            )
                            else "failed"
                        )
                        continue
                    selected = case.criterion
                    case.status = (
                        "automatic_pass"
                        if selected is not None and check_expected(selected.expected, result)
                        else "failed"
                    )
                except RuntimeError, ValueError, httpx.HTTPError:
                    case.status = "failed"
                    case.explanation = "Assessment failed; no acceptance claimed."
    by_id = {c.case: c for c in cases}
    for case in cases:
        if case.personalized_expected is None or case.personalized_result is None:
            continue
        for name, expected in case.personalized_expected.criteria.items():
            if expected.relative_to is None:
                continue
            other = by_id.get(expected.relative_to)
            if other is None or other.personalized_result is None:
                case.status = "failed"
                continue
            score = next(
                d.score for d in case.personalized_result.dimensions if d.dimension_id == name
            )
            other_score = next(
                d.score for d in other.personalized_result.dimensions if d.dimension_id == name
            )
            if (
                score is None
                or other_score is None
                or not (
                    score > other_score if expected.direction == "higher" else score < other_score
                )
            ):
                case.status = "failed"
    # Git history is read only; command and repository path are fixed local inputs.
    revision = subprocess.run(  # noqa: S603 - fixed read-only local git command.
        [shutil.which("git") or "/usr/bin/git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    run = Run(
        timestamp=datetime.now(UTC).isoformat(),
        git_revision=revision,
        source_hash=source_hash(),
        model=model,
        prompt_hash=digest(INSTRUCTIONS.encode()),
        schema_hash=digest(
            json.dumps(WorkArrangementResult.model_json_schema(), sort_keys=True).encode()
        ),
        criterion="mixed",
        readiness_issues=issues,
        cases=cases,
        limitations=[
            "Manual findings, evidence relevance and report usability need owner review.",
            "Replay and coverage do not establish semantic quality.",
        ],
    )
    run.run_id = run_fingerprint(run)
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check", action="store_true", help="Offline corpus readiness only")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--recordings-dir", type=Path, help="Capture sanitized inference SSE only")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, help="Existing run to review without new inference")
    parser.add_argument("--manual-review", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.review is not None:
            if args.manual_review is None or args.live or args.check:
                raise ValueError("Review mode requires --manual-review and no --live/--check.")
            run = Run.model_validate_json(args.review.read_bytes())
            review = ManualReview.model_validate_json(args.manual_review.read_bytes())
            accept_review(run, review)
        else:
            if args.live == args.check or args.manual_review is not None:
                raise ValueError("Select exactly one of --live or --check.")
            manifest = Manifest.model_validate_json((ROOT / "manifest.json").read_bytes())
            run = evaluate(manifest, args.model, live=args.live, recordings=args.recordings_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(run.model_dump_json(indent=2) + "\n")
        print(f"Wrote evaluation report: {args.output}; accepted={run.accepted}")
        return 0 if run.accepted else 1
    except ValueError, OSError, RuntimeError:
        print(
            "Evaluation failed: invalid corpus, review, credentials, or output path.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
