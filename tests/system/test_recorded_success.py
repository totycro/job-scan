"""Actual provider cassettes exercise the entire successful CLI workflow offline."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from job_scan.ai import DEFAULT_MODEL, ResponsesClient, request_body
from job_scan.auth import RESOURCE
from job_scan.cli import main
from job_scan.models import WorkArrangementResult
from tests.conftest import Replay

ROOT = Path(__file__).resolve().parents[2]
CASE_PATHS = [
    entry["posting"].removesuffix("/posting.html")
    for entry in json.loads((ROOT / "evaluations/manifest.json").read_text())["required_cases"]
    if entry["mode"] == "work_arrangement"
]


@pytest.mark.parametrize("case_path", CASE_PATHS)
def test_recorded_assessment(
    case_path: str,
    signed_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = ROOT / "evaluations" / case_path / "posting.html"
    annotation = json.loads(path.with_name("expected.json").read_text())["criteria"][
        "work_arrangement"
    ]
    expected = annotation["expected"].get("posting_status", "identified")
    request = httpx.Request(
        "POST", RESOURCE + "/responses", json=request_body(path.read_text(), DEFAULT_MODEL)
    )
    cassette = (
        ROOT
        / "tests/recordings/inference"
        / f"actual-{hashlib.sha256(request.content).hexdigest()}.json"
    )
    if not cassette.exists():
        pytest.fail(f"Missing actual provider recording for {case_path}: {cassette}")
    if case_path in {"cases/posting-02", "fixtures/remote-restrictions"}:
        recorded = json.loads(cassette.read_text())["exchanges"][0]["body"]
        text, _ = ResponsesClient.read_stream(httpx.Response(200, text=recorded))
        result = WorkArrangementResult.model_validate_json(text)
        generated = " ".join(
            [a.context for a in result.arrangements]
            + [s.context for s in result.home_working]
            + result.uncertainties
        ).casefold()
        for excluded in ("europe", "germany", "time zone", "timezone", "right to work", "cet"):
            assert excluded not in generated
    replay = Replay.load(cassette)
    real_client = httpx.Client

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(replay))

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    outcome = main(["assess", str(path)])
    captured = capsys.readouterr()
    assert outcome == (0 if expected == "identified" else 1)
    if expected == "identified":
        assert "Source:" in captured.out and "Fit:" in captured.out and "Evidence:" in captured.out
        assert not captured.err
    else:
        assert not captured.out and captured.err
    assert not replay.exchanges


def test_url_assessment_reuses_recorded_findings_with_retrieved_evidence(
    signed_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reuse an actual response; this is not a recording of a live URL assessment."""
    from job_scan.retrieval import Document, assemble_documents

    html = (ROOT / "evaluations/cases/posting-01/posting.html").read_text()
    original = httpx.Request(
        "POST", RESOURCE + "/responses", json=request_body(html, DEFAULT_MODEL)
    )
    cassette = (
        ROOT
        / "tests/recordings/inference"
        / ("actual-" + hashlib.sha256(original.content).hexdigest() + ".json")
    )
    recorded = json.loads(cassette.read_text())["exchanges"][0]
    url = "https://jobs.example/?job=42#selected"
    source = assemble_documents(url, [Document("https://ats.example/job/42", html)])
    monkeypatch.setattr("job_scan.cli.retrieve_posting", lambda _url: source)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        data = json.loads(payload["input"][0]["content"])
        assert data == {"html": source.html, "target_url": url}
        return httpx.Response(recorded["status"], text=recorded["body"])

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "Client", client)
    assert main(["assess", url]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert f"URL: {url}" in captured.out
    assert "Final page URL: https://ats.example/job/42" in captured.out
    assert "Evidence:" in captured.out
