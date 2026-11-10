"""Successful personalized paths require actual sanitized provider recordings."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from evaluations.run import Manifest
from job_scan.ai import DEFAULT_MODEL, exception_request_body, fit_request_body, request_body
from job_scan.auth import RESOURCE
from job_scan.cli import load_posting, load_profile, main
from job_scan.profiles import has_exceptions
from tests.conftest import Replay

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Manifest.model_validate_json((ROOT / "evaluations/manifest.json").read_bytes())


@pytest.mark.parametrize(
    "pair_id", [e.id for e in MANIFEST.required_cases if e.mode == "personalized"]
)
def test_recorded_personalized_assessment(
    pair_id: str,
    signed_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    url_input: bool = False,
) -> None:
    entry = next(e for e in MANIFEST.required_cases if e.id == pair_id)
    assert entry.profile is not None
    posting = ROOT / "evaluations" / entry.posting
    profile_path = ROOT / "evaluations" / entry.profile
    original = profile_path.read_bytes()
    source, profile = load_posting(posting), load_profile(profile_path)
    bodies = [
        request_body(source.html, DEFAULT_MODEL),
        fit_request_body(source.html, profile.profile, DEFAULT_MODEL),
    ]
    if has_exceptions(profile.profile):
        bodies.append(exception_request_body(source.html, profile.profile, DEFAULT_MODEL))
    exchanges: list[dict[str, object]] = []
    url = "https://jobs.example/job/42"
    for body in bodies:
        request = httpx.Request("POST", RESOURCE + "/responses", json=body)
        cassette = (
            ROOT
            / "tests/recordings/inference"
            / ("actual-" + hashlib.sha256(request.content).hexdigest() + ".json")
        )
        if not cassette.exists():
            pytest.fail(
                f"Missing actual provider recording for {pair_id}: {cassette.name}; "
                "capture via T054 after owner content review"
            )
        payload = json.loads(cassette.read_bytes())
        assert "actual-provider" in payload["provenance"]
        if url_input and body is bodies[0]:
            adapted = httpx.Request(
                "POST", RESOURCE + "/responses", json=request_body(source.html, DEFAULT_MODEL, url)
            )
            # Reuse recorded source findings, not a purported live URL request recording.
            payload["exchanges"][0]["request_sha256"] = hashlib.sha256(adapted.content).hexdigest()
        exchanges.extend(payload["exchanges"])
    replay = Replay(exchanges)
    real_client = httpx.Client

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(replay))

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    if url_input:
        retrieved = source.model_copy(update={"path": None, "source_url": url, "final_url": url})
        monkeypatch.setattr("job_scan.cli.retrieve_posting", lambda _url: retrieved)
    assert main(["assess", url if url_input else str(posting), "--profile", str(profile_path)]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert str(profile_path) in captured.out
    for label in [
        "Work arrangement",
        "Role fit",
        "Technology fit",
        "Field interest",
        "Company affinity",
        "Weighted overall",
        "Decisive outcome",
    ]:
        assert label in captured.out
    assert not replay.exchanges
    expected = json.loads((ROOT / "evaluations" / entry.expectations).read_bytes())
    overall = expected["overall"]
    assert (
        f"Dimensions rated: {overall['rated_dimension_count']}/"
        f"{overall['configured_dimension_count']}"
    ) in captured.out
    assert (
        f"importance coverage: {overall['rated_importance']}/"
        f"{overall['total_configured_importance']}"
    ) in captured.out
    outcome_labels = {
        "deal_breaker": "deal-breaker",
        "no_exception_applies": "no exceptional preference applies",
    }
    code = expected["decisive_code"]
    assert outcome_labels.get(code, code.replace("_", " ")) in captured.out
    if overall["status"] == "unavailable":
        assert "/100" not in captured.out
        assert "Unavailable" in captured.out
    elif overall["status"] == "partial":
        assert "Partial overall" in captured.out
    for name in overall["missing_dimension_ids"]:
        assert f"Missing {name.replace('_', ' ').capitalize()}" in captured.out
    if overall["rated_dimension_count"]:
        assert "approximate contribution" in captured.out
    assert len(bodies) == (3 if has_exceptions(profile.profile) else 2)
    for dimension in profile.profile.dimensions.values():
        for declaration in dimension.exceptions:
            assert declaration.id in captured.out
            assert declaration.preference_quote in captured.out
            assert declaration.kind.replace("_", " ") in captured.out
    assert profile_path.read_bytes() == original


def test_distinct_profiles_across_invocations(
    signed_session: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for pair_id in ["role-contrast-high", "role-contrast-low"]:
        with monkeypatch.context() as isolated:
            test_recorded_personalized_assessment(pair_id, signed_session, isolated, capsys)


def test_recorded_url_personalized_assessment(
    signed_session: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    test_recorded_personalized_assessment(
        "opposing-same-dimension", signed_session, monkeypatch, capsys, url_input=True
    )
