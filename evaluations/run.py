"""Opt-in live golden evaluation and bound manual review; never rewrites expectations."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, JsonValue

from job_scan.ai import DEFAULT_MODEL, Event, ResponsesClient, request_body
from job_scan.auth import RESOURCE, ChatGPTSession
from job_scan.cli import load_posting
from job_scan.criteria.work_arrangement import INSTRUCTIONS, PROMPT_VERSION
from job_scan.evidence import assess, resolve
from job_scan.models import Evidence, Kind, Model, WorkArrangementResult
from job_scan.report import render

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


class Manifest(Model):
    criterion: Literal["work_arrangement"]
    required_cases: list[str]


class CaseResult(BaseModel):
    case: str
    criterion: Criterion | None = None
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
    for case in run.cases:
        path = ROOT / case.case
        if (
            digest((path / "posting.html").read_bytes()) != case.input_hash
            or digest((path / "expected.json").read_bytes()) != case.expectation_file_hash
            or digest((path / "metadata.json").read_bytes()) != case.metadata_file_hash
        ):
            raise ValueError(
                "Case content, expectations or content review changed; rerun evaluation."
            )
    run.review = review
    run.accepted = bool(run.cases) and all(
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


def evaluate(manifest: Manifest, model: str, *, live: bool, recordings: Path | None = None) -> Run:
    cases = [inspect_case(ROOT / path, manifest.criterion) for path in manifest.required_cases]
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
                source = load_posting(ROOT / case.case / "posting.html")
                case.request_hash = digest(
                    json.dumps(request_body(source.html, model), sort_keys=True).encode()
                )
                try:
                    result = client.assess_html(source.html, model)
                    case.result = result
                    case.returned_model = client.returned_model
                    if result.posting_status == "identified":
                        case.report = render(assess(source, result, client.returned_model or model))
                    else:
                        case.report = result.posting_explanation
                    selected = case.criterion
                    case.status = (
                        "automatic_pass"
                        if selected is not None and check_expected(selected.expected, result)
                        else "failed"
                    )
                except RuntimeError, ValueError, httpx.HTTPError:
                    case.status = "failed"
                    case.explanation = "Assessment failed; no acceptance claimed."
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
        criterion=manifest.criterion,
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
