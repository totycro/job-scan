from pathlib import Path

import pytest

from evaluations.run import Expected, check_expected, inspect_case
from job_scan.models import WorkArrangementResult


def test_projection(remote_result: dict[str, object]) -> None:
    result = WorkArrangementResult.model_validate(remote_result)
    assert check_expected(Expected.model_validate({"arrangement": "remote"}), result)
    assert not check_expected(Expected.model_validate({"arrangement": "hybrid"}), result)
    assert check_expected(
        Expected.model_validate(
            {"home_working_schedule": {"status": "not_stated", "days_text": None, "period": None}}
        ),
        result,
    )
    result.arrangements[0].kind = "hybrid"
    result.home_working = []
    assert check_expected(Expected.model_validate({"arrangement": ["hybrid"]}), result)
    with pytest.raises(ValueError):
        Expected.model_validate({"unknown_expectation": "pass"})


def test_approved_corpus() -> None:
    case = inspect_case(Path("evaluations/cases/posting-01"), "work_arrangement")
    assert case.status == "ready"
    assert case.input_hash == case.expected_hash
    assert case.criterion is not None
    assert case.criterion.review_status == "approved"


def test_schedule_and_arrangement_projection(remote_result: dict[str, object]) -> None:
    from job_scan.models import Schedule

    result = WorkArrangementResult.model_validate(remote_result)
    result.home_working = [
        Schedule(
            kind="allowed",
            days_text=None,
            period=None,
            context="Engineer",
            evidence=result.arrangements[0].evidence,
        )
    ]
    assert not check_expected(
        Expected.model_validate(
            {"home_working_schedule": {"status": "not_stated", "days_text": None}}
        ),
        result,
    )
    assert check_expected(
        Expected.model_validate(
            {
                "home_working_schedule": {
                    "status": "stated",
                    "kind": "allowed",
                    "days_text": None,
                    "period": None,
                }
            }
        ),
        result,
    )
    result.home_working[0].days_text = "2 days"
    result.home_working[0].period = "per week"
    assert not check_expected(
        Expected.model_validate({"home_working_schedule": {"days_text": None}}), result
    )
    assert check_expected(
        Expected.model_validate(
            {"home_working_schedule": {"days_text": "2 days", "period": "per week"}}
        ),
        result,
    )
    result.home_working.append(result.home_working[0])
    assert not check_expected(Expected.model_validate({"home_working_schedule": {}}), result)
    result.arrangements.append(result.arrangements[0].model_copy(update={"kind": "onsite"}))
    assert not check_expected(Expected.model_validate({"arrangement": "remote"}), result)
    assert check_expected(Expected.model_validate({"arrangement": ["remote", "onsite"]}), result)
    for expected in ({"arrangement": None}, {"home_working_schedule": None}):
        with pytest.raises(ValueError):
            check_expected(Expected.model_validate(expected), result)
    result.posting_status = "absent"
    result.posting_explanation = "No posting"
    assert check_expected(Expected.model_validate({"posting_status": "absent"}), result)
    assert not check_expected(Expected.model_validate({}), result)
    assert not check_expected(Expected.model_validate({"posting_status": "identified"}), result)


def test_annotation_readiness(tmp_path: Path) -> None:
    import hashlib
    import json

    path = tmp_path / "case"
    path.mkdir()
    html = "<h1>Engineer</h1>Fully remote"
    sha = hashlib.sha256(html.encode()).hexdigest()
    (path / "posting.html").write_text(html)
    meta = {
        "schema_version": 1,
        "case_id": "case",
        "content_review_status": "approved",
        "posting_sha256": sha,
    }
    annotation = {"schema_version": 1, "case_id": "case", "criteria": {}}
    (path / "metadata.json").write_text(json.dumps(meta))
    (path / "expected.json").write_text(json.dumps(annotation))
    assert inspect_case(path, "work_arrangement").status == "not_evaluated"
    selected = {
        "review_status": "approved",
        "expectation_authorship": "Synthetic test",
        "posting_sha256": sha,
        "expected": {"arrangement": "remote"},
        "evidence": [{"quote": "Fully remote", "occurrence": 0}],
        "required_findings": [],
        "prohibited_conclusions": [],
    }
    annotation["criteria"] = {
        "work_arrangement": selected,
        "future_criterion": {"expected": {"unrelated_shape": True}},
    }
    (path / "expected.json").write_text(json.dumps(annotation))
    assert inspect_case(path, "work_arrangement").status == "ready"
    selected["posting_sha256"] = "stale"
    (path / "expected.json").write_text(json.dumps(annotation))
    assert inspect_case(path, "work_arrangement").status == "stale"


def test_offline_report_and_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    from evaluations.run import ManualReview, Run, accept_review, main, run_fingerprint

    out = tmp_path / "run.json"
    assert main(["--check", "--output", str(out)]) == 1
    run = Run.model_validate_json(out.read_bytes())
    assert run.run_id == run_fingerprint(run)
    assert not run.accepted
    review = ManualReview(run_id=run.run_id, reviewer="Owner", cases={})
    assert not accept_review(run, review)
    with pytest.raises(ValueError, match="immutable"):
        accept_review(run, review.model_copy(update={"run_id": "wrong"}))
    changed = run.model_copy(update={"source_hash": "stale"})
    changed.run_id = run_fingerprint(changed)
    with pytest.raises(ValueError, match="code changed"):
        accept_review(changed, review.model_copy(update={"run_id": changed.run_id}))
    manual = tmp_path / "review.json"
    manual.write_text(json.dumps(review.model_dump()))
    assert main(["--review", str(out), "--manual-review", str(manual), "--output", str(out)]) == 1
    assert main(["--output", str(out)]) == 1
    assert main(["--review", str(out), "--output", str(out)]) == 1
    monkeypatch.setattr("evaluations.run.source_hash", lambda: "changed")
    with pytest.raises(ValueError):
        accept_review(run, review)


def test_recording_omits_oauth(tmp_path: Path) -> None:
    import httpx

    from evaluations.run import Recorder

    recorder = Recorder(tmp_path)
    request = httpx.Request("POST", "https://auth.openai.com/api/accounts/oauth/token")
    recorder.response(httpx.Response(200, request=request, json={"access_token": "never-record"}))
    assert not list(tmp_path.iterdir())


def test_manual_checks_and_source_review_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    import evaluations.run as evaluation

    path = tmp_path / "case"
    path.mkdir()
    (path / "posting.html").write_text("Synthetic")
    (path / "expected.json").write_text("{}")
    (path / "metadata.json").write_text("{}")
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "source_hash", lambda: "synthetic-revision")
    case = evaluation.CaseResult(
        case="case",
        input_hash=evaluation.digest(b"Synthetic"),
        expectation_file_hash=evaluation.digest(b"{}"),
        metadata_file_hash=evaluation.digest(b"{}"),
        status="automatic_pass",
    )
    run = evaluation.Run(
        timestamp="synthetic",
        git_revision="synthetic",
        source_hash="synthetic-revision",
        model="test",
        prompt_hash="test",
        schema_hash="test",
        criterion="work_arrangement",
        cases=[case],
        limitations=["Synthetic unit test, no owner approval claimed."],
    )
    run.run_id = evaluation.run_fingerprint(run)
    checks = evaluation.ManualChecks(
        semantic_findings=True,
        evidence_relevance=True,
        prohibited_conclusions_absent=True,
        report_usable=True,
        notes="Synthetic unit test.",
    )
    review = evaluation.ManualReview(
        run_id=run.run_id, reviewer="Synthetic test", cases={"case": checks}
    )
    assert evaluation.accept_review(run, review)
    checks.evidence_relevance = False
    assert not evaluation.accept_review(run, review)
    (path / "metadata.json").write_text(
        json.dumps({"content_review_status": "pending_owner_review"})
    )
    with pytest.raises(ValueError, match="review changed"):
        evaluation.accept_review(run, review)
