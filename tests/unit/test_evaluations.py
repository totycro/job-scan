import json
from pathlib import Path

import pytest

from evaluations.run import Expected, check_expected, inspect_case
from job_scan.models import WorkArrangementResult


@pytest.fixture
def pending_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate pending-review gates from the real corpus's current owner approval."""
    import shutil

    import evaluations.run as evaluation

    root = tmp_path / "evaluations"
    shutil.copytree(evaluation.ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(evaluation.ROOT.parent / "uv.lock", tmp_path / "uv.lock")
    manifest = evaluation.Manifest.model_validate_json((root / "manifest.json").read_bytes())
    entry = next(e for e in manifest.required_cases if e.mode == "personalized")
    for relative, field in [
        (entry.expectations, "review_status"),
        (str(Path(entry.posting).with_name("metadata.json")), "content_review_status"),
    ]:
        path = root / relative
        content = json.loads(path.read_bytes())
        content[field] = "pending_owner_review"
        path.write_text(json.dumps(content))
    monkeypatch.setattr(evaluation, "ROOT", root)
    return root


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
    with pytest.raises(ValueError, match="complete required"):
        accept_review(run, review)
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
    import shutil

    for name in ["posting.html", "expected.json", "metadata.json"]:
        shutil.copyfile(Path("evaluations/cases/posting-01") / name, path / name)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "required_cases": [
                    {
                        "id": "case",
                        "mode": "work_arrangement",
                        "posting": "case/posting.html",
                        "profile": None,
                        "expectations": "case/expected.json",
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "source_hash", lambda: "synthetic-revision")
    monkeypatch.setattr(evaluation, "coverage_issues", lambda _manifest: [])
    case = evaluation.CaseResult(
        case="case",
        input_hash=evaluation.digest((path / "posting.html").read_bytes()),
        expectation_file_hash=evaluation.digest((path / "expected.json").read_bytes()),
        metadata_file_hash=evaluation.digest((path / "metadata.json").read_bytes()),
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


def test_manifest_v2_contract() -> None:
    import json

    from evaluations.run import Manifest

    contents = json.loads(Path("evaluations/manifest.json").read_text())
    manifest = Manifest.model_validate(contents)
    assert manifest.schema_version == 2
    assert len({e.id for e in manifest.required_cases}) == len(manifest.required_cases)
    assert any(
        e.id == "cases/posting-01" and e.mode == "work_arrangement" for e in manifest.required_cases
    )
    for dimension in ["role", "technology", "field", "affinity"]:
        assert (
            len([e for e in manifest.required_cases if e.id.startswith(dimension + "-contrast-")])
            == 2
        )
    entry = {
        "id": "pair",
        "mode": "personalized",
        "posting": "x/posting.html",
        "profile": "profiles/x.toml",
        "expectations": "x/expected.json",
    }
    for invalid in [
        {**entry, "profile": None},
        {**entry, "mode": "unknown"},
        {**entry, "mode": "work_arrangement"},
        {**entry, "extra": True},
    ]:
        with pytest.raises(ValueError):
            Manifest.model_validate({"schema_version": 2, "required_cases": [invalid]})
    with pytest.raises(ValueError):
        Manifest.model_validate({"schema_version": 2, "required_cases": [entry, entry]})


def test_personalized_readiness_and_strict_expectations(pending_corpus: Path) -> None:
    from evaluations.run import Manifest, PersonalizedExpected, inspect_entry

    manifest = Manifest.model_validate_json((pending_corpus / "manifest.json").read_bytes())
    entry = next(e for e in manifest.required_cases if e.mode == "personalized")
    case = inspect_entry(entry)
    assert case.status == "pending_review"
    assert case.profile_hash is not None
    data = json.loads((pending_corpus / entry.expectations).read_text())
    PersonalizedExpected.model_validate_json(json.dumps(data))
    for invalid in [{**data, "surprise": True}, {**data, "criteria": {"unknown": {}}}]:
        with pytest.raises(ValueError):
            PersonalizedExpected.model_validate_json(json.dumps(invalid))


@pytest.mark.parametrize(
    "change",
    [
        "profile",
        "posting",
        "expectations",
        "metadata",
        "manifest",
        "code",
        "lockfile",
        "prompt",
        "schema",
        "run-id",
        "missing-run",
        "duplicate-run",
        "missing-review",
        "extra-review",
    ],
)
def test_personalized_review_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    import shutil

    import evaluations.run as evaluation

    original_root = evaluation.ROOT
    entry = next(
        e
        for e in evaluation.Manifest.model_validate_json(
            (original_root / "manifest.json").read_bytes()
        ).required_cases
        if e.mode == "personalized"
    )
    root = tmp_path / "evaluations"
    root.mkdir()
    assert entry.profile is not None
    for relative in [
        entry.posting,
        entry.profile,
        entry.expectations,
        str(Path(entry.posting).with_name("metadata.json")),
    ]:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original_root / relative, destination)
    for relative, field in [
        (entry.expectations, "review_status"),
        (str(Path(entry.posting).with_name("metadata.json")), "content_review_status"),
    ]:
        content = json.loads((root / relative).read_text())
        content[field] = "approved"  # Synthetic copied corpus only; no actual owner approval.
        (root / relative).write_text(json.dumps(content))
    monkeypatch.setattr(evaluation, "coverage_issues", lambda _manifest: [])
    manifest = evaluation.Manifest(schema_version=2, required_cases=[entry])
    (root / "manifest.json").write_text(manifest.model_dump_json())
    (tmp_path / "uv.lock").write_text("synthetic lock")
    code = tmp_path / "src/job_scan"
    code.mkdir(parents=True)
    for file in ["app.py", "prompt.py", "schema.py"]:
        (code / file).write_text("# synthetic unit-test code binding\n")
    monkeypatch.setattr(evaluation, "ROOT", root)
    case = evaluation.inspect_entry(entry)
    case.status = "automatic_pass"  # Synthetic review-binding unit test, not actual approval.
    run = evaluation.Run(
        timestamp="synthetic",
        git_revision="test",
        source_hash=evaluation.source_hash(),
        model="synthetic",
        prompt_hash="test",
        schema_hash="test",
        criterion="mixed",
        cases=[case],
        limitations=["Synthetic binding test only."],
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
        run_id=run.run_id, reviewer="Synthetic test", cases={entry.id: checks}
    )
    assert evaluation.accept_review(run, review)
    targets = {
        "profile": root / entry.profile,
        "posting": root / entry.posting,
        "expectations": root / entry.expectations,
        "metadata": (root / entry.posting).with_name("metadata.json"),
        "manifest": root / "manifest.json",
        "code": code / "app.py",
        "lockfile": tmp_path / "uv.lock",
        "prompt": code / "prompt.py",
        "schema": code / "schema.py",
    }
    if change in targets:
        with targets[change].open("a") as stream:
            stream.write(" ")
    elif change == "run-id":
        review.run_id = "wrong"
    elif change == "missing-run":
        run.cases = []
    elif change == "duplicate-run":
        run.cases.append(case)
    elif change == "missing-review":
        review.cases = {}
    else:
        review.cases["unexpected"] = checks
    with pytest.raises(ValueError):
        evaluation.accept_review(run, review)


def test_live_refuses_pending_before_auth(
    monkeypatch: pytest.MonkeyPatch, pending_corpus: Path
) -> None:
    import evaluations.run as evaluation

    manifest = evaluation.Manifest.model_validate_json(
        (pending_corpus / "manifest.json").read_bytes()
    )

    def forbidden() -> None:
        pytest.fail("Pending corpus review must not open an authenticated session")

    monkeypatch.setattr(evaluation, "ChatGPTSession", forbidden)
    with pytest.raises(ValueError, match="ready"):
        evaluation.evaluate(manifest, "synthetic", live=True)


def test_readiness_requires_mandatory_groups() -> None:
    from evaluations.run import Manifest, coverage_issues

    manifest = Manifest.model_validate_json(Path("evaluations/manifest.json").read_bytes())
    assert coverage_issues(manifest) == []
    reduced = manifest.model_copy(
        update={
            "required_cases": [
                e for e in manifest.required_cases if e.id != "partial-required-unknown"
            ]
        }
    )
    assert any("partial-required-unknown" in issue for issue in coverage_issues(reduced))


def test_pending_corpus_cannot_accept_synthetic_pass_flags(pending_corpus: Path) -> None:
    import evaluations.run as evaluation

    manifest = evaluation.Manifest.model_validate_json(
        (pending_corpus / "manifest.json").read_bytes()
    )
    run = evaluation.evaluate(manifest, "synthetic-no-inference", live=False)
    for case in run.cases:
        case.status = (
            "automatic_pass"  # Deliberately forged unit input; must not bypass review readiness.
        )
    run.run_id = evaluation.run_fingerprint(run)
    checks = evaluation.ManualChecks(
        semantic_findings=True,
        evidence_relevance=True,
        prohibited_conclusions_absent=True,
        report_usable=True,
        notes="Synthetic bypass test.",
    )
    review = evaluation.ManualReview(
        run_id=run.run_id, reviewer="Synthetic test", cases={c.case: checks for c in run.cases}
    )
    with pytest.raises(ValueError, match="not ready"):
        evaluation.accept_review(run, review)


@pytest.mark.parametrize("success", [True, False])
def test_stage_trace_has_models_hashes_timing_and_outcome(
    signed_session: Path, success: bool
) -> None:
    import httpx

    from evaluations.run import CaseResult, evaluate_stage
    from job_scan.ai import ResponsesClient, fit_request_body
    from job_scan.auth import ChatGPTSession
    from job_scan.profiles import Profile
    from job_scan.rating_models import FitResponse
    from tests.conftest import fictional_profile
    from tests.system.test_personalized_failures import completed

    case = CaseResult(
        case="synthetic",
        input_hash="test",
        expectation_file_hash="test",
        metadata_file_hash="test",
        status="ready",
    )
    profile = Profile.model_validate(fictional_profile())
    body = fit_request_body("HTML", profile, "chosen")
    response = (
        completed({"dimensions": []}) if success else httpx.Response(500, text="PRIVATE-PROVIDER")
    )
    with (
        ChatGPTSession(signed_session / "job-scan") as session,
        ResponsesClient(
            session, httpx.Client(transport=httpx.MockTransport(lambda _r: response))
        ) as client,
    ):

        def action() -> FitResponse:
            return client.request_structured(
                "unit instructions", "{}", "fit", FitResponse, "chosen"
            )

        if success:
            assert (
                evaluate_stage(case, client, "fit", "chosen", body, "test-v1", action).dimensions
                == []
            )
        else:
            with pytest.raises(RuntimeError):
                evaluate_stage(case, client, "fit", "chosen", body, "test-v1", action)
    trace = case.stages[0]
    assert trace.outcome == ("completed" if success else "failed")
    assert trace.seconds >= 0
    assert len(trace.prompt_hash) == len(trace.schema_hash) == len(trace.request_hash) == 64
    assert trace.requested_model == "chosen"
    assert trace.returned_model == ("synthetic-test-only" if success else None)
    assert trace.result == ({"dimensions": []} if success else None)
    assert "PRIVATE-PROVIDER" not in case.model_dump_json()


def test_personalized_automatic_assertions() -> None:
    import copy

    from evaluations.run import Manifest, PersonalizedExpected, check_personalized
    from job_scan.cli import load_posting, load_profile
    from job_scan.rating_models import FitResponse
    from job_scan.ratings import assemble
    from tests.conftest import fixed_rating
    from tests.unit.test_ratings import work

    manifest = Manifest.model_validate_json(Path("evaluations/manifest.json").read_bytes())
    entry = next(e for e in manifest.required_cases if e.id == "role-contrast-high")
    assert entry.profile is not None
    source = load_posting(Path("evaluations") / entry.posting)
    profile = load_profile(Path("evaluations") / entry.profile)
    expected = PersonalizedExpected.model_validate_json(
        (Path("evaluations") / entry.expectations).read_bytes()
    )
    fit = fixed_rating("role_fit")
    fit["findings"][0]["evidence"] = [
        e.model_dump() for e in expected.criteria["role_fit"].evidence
    ]
    report = assemble(work(source), profile, FitResponse.model_validate({"dimensions": [fit]}), [])
    assert check_personalized(expected, report)
    for change in ["band", "state", "evidence", "exception", "overall", "decisive"]:
        changed = copy.deepcopy(expected)
        criterion = changed.criteria["role_fit"]
        if change == "band":
            criterion.score_band = (0, 40)
        elif change == "state":
            criterion.state = "insufficient_evidence"
        elif change == "evidence":
            criterion.evidence[0].quote = "Not in source"
        elif change == "exception":
            criterion.exceptions = {"invented": "matched"}
        elif change == "overall":
            changed.overall.status = "partial"
        else:
            changed.decisive_code = "deal_breaker"
        assert not check_personalized(changed, report)


def test_expected_passages_allow_narrow_citations_but_preserve_occurrence() -> None:
    from evaluations.run import Manifest, PersonalizedExpected, check_personalized
    from job_scan.cli import load_posting, load_profile
    from job_scan.rating_models import FitResponse
    from job_scan.ratings import assemble
    from tests.conftest import fixed_rating
    from tests.unit.test_ratings import work

    manifest = Manifest.model_validate_json(Path("evaluations/manifest.json").read_bytes())
    entry = next(e for e in manifest.required_cases if e.id == "role-contrast-high")
    assert entry.profile is not None
    source = load_posting(Path("evaluations") / entry.posting)
    profile = load_profile(Path("evaluations") / entry.profile)
    expected = PersonalizedExpected.model_validate_json(
        (Path("evaluations") / entry.expectations).read_bytes()
    )
    fit = fixed_rating("role_fit")
    # The golden annotation identifies a full sentence; a narrower exact source quote is valid.
    fit["findings"][0]["evidence"] = [{"quote": "hands-on backend development", "occurrence": 0}]
    response = FitResponse.model_validate({"dimensions": [fit]})
    result = assemble(work(source), profile, response, [])
    assert check_personalized(expected, result)
    # Identical wording elsewhere in the HTML does not satisfy the expected passage location.
    source.html += source.html
    fit["findings"][0]["evidence"][0]["occurrence"] = 1
    response = FitResponse.model_validate({"dimensions": [fit]})
    result = assemble(work(source), profile, response, [])
    assert not check_personalized(expected, result)


def test_contrasting_pairs_can_share_one_posting_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    import evaluations.run as evaluation

    original = evaluation.ROOT
    manifest = evaluation.Manifest.model_validate_json((original / "manifest.json").read_bytes())
    entries = [
        e for e in manifest.required_cases if e.id in {"role-contrast-high", "role-contrast-low"}
    ]
    root = tmp_path / "evaluations"
    shared = root / "shared"
    shared.mkdir(parents=True)
    first = next(e for e in entries if e.id == "role-contrast-high")
    shutil.copyfile(original / first.posting, shared / "posting.html")
    shutil.copyfile((original / first.posting).with_name("metadata.json"), shared / "metadata.json")
    for entry in entries:
        assert entry.profile is not None
        for relative in [entry.profile, entry.expectations]:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / relative, destination)
    monkeypatch.setattr(evaluation, "ROOT", root)
    for entry in entries:
        shared_entry = entry.model_copy(update={"posting": "shared/posting.html"})
        case = evaluation.inspect_entry(shared_entry)
        assert case.status == "ready"
        assert case.case == entry.id
    # Pair-specific expectations still bind to their own unique pair identity.
    wrong = entries[0].model_copy(update={"id": "unrelated-pair", "posting": "shared/posting.html"})
    with pytest.raises(ValueError, match="identity"):
        evaluation.inspect_entry(wrong)
