"""Synthetic failure injection at HTTP boundaries; no actual-success provenance claimed."""

import json
from pathlib import Path

import httpx
import pytest

from job_scan.cli import main
from job_scan.profiles import DIMENSION_IDS
from tests.conftest import fixed_rating


def profile_file(tmp_path: Path, *, declarations: bool = True) -> Path:
    text = "schema_version = 1\n" + "\n".join(
        f'[dimensions.{name}]\nimportance = 1\npreferences = "I want backend development."\n'
        for name in DIMENSION_IDS
    )
    if declarations:
        text += (
            '\n[[dimensions.role_fit.exceptions]]\nid = "x"\nkind = "deal_breaker"\n'
            'preference_quote = "backend development"\n'
        )
    path = tmp_path / "fictional.toml"
    path.write_text(text)
    return path


def completed(data: object) -> httpx.Response:
    return httpx.Response(
        200,
        text="data: "
        + json.dumps(
            {
                "type": "response.completed",
                "response": {
                    "model": "synthetic-test-only",
                    "output": [{"content": [{"type": "output_text", "text": json.dumps(data)}]}],
                },
            }
        )
        + "\n\n",
    )


@pytest.mark.parametrize("stage", [0, 1, 2])
@pytest.mark.parametrize(
    "failure",
    ["http", "schema", "quote", "incomplete", "refusal", "timeout", "interruption", "registration"],
)
def test_atomic_stage_failure(
    stage: int,
    failure: str,
    signed_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    remote_result: dict[str, object],
) -> None:
    posting = tmp_path / "posting.html"
    posting.write_text("Fully remote backend development")
    profile = profile_file(tmp_path)
    fits = {"dimensions": [fixed_rating(name) for name in DIMENSION_IDS]}
    exceptions = {
        "exceptions": [
            {
                "exception_id": "x",
                "status": "matched",
                "explanation": "Synthetic match.",
                "evidence": [{"quote": "backend development", "occurrence": 0}],
            }
        ]
    }
    data = json.loads(json.dumps([remote_result, fits, exceptions]))
    count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal count
        current = count
        count += 1
        if current < stage:
            return completed(data[current])
        assert current == stage, "Failure must stop subsequent inference"
        if failure == "http":
            return httpx.Response(500, text="PRIVATE-PROVIDER")
        if failure == "schema":
            return completed({"PRIVATE-PROFILE": "PRIVATE-PROVIDER"})
        if failure == "quote":
            if stage == 0:
                data[0]["arrangements"][0]["evidence"][0]["quote"] = "PRIVATE-PROVIDER"
            elif stage == 1:
                data[1]["dimensions"][0]["findings"][0]["evidence"][0]["quote"] = "PRIVATE-PROVIDER"
            else:
                data[2]["exceptions"][0]["evidence"][0]["quote"] = "PRIVATE-PROVIDER"
            return completed(data[current])
        if failure in {"incomplete", "refusal"}:
            event = "response.incomplete" if failure == "incomplete" else "response.refusal.done"
            return httpx.Response(200, text="data: " + json.dumps({"type": event}) + "\n\n")
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE-PROVIDER")
        if failure == "interruption":
            raise KeyboardInterrupt
        from job_scan.auth import ChatGPTSession

        session = ChatGPTSession(signed_session / "job-scan")
        with session.locked():
            store = session.load()
            store.active = None
            session.save(store)
        session.client.close()
        return completed(data[current])

    real_client = httpx.Client

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    assert main(["assess", str(posting), "--profile", str(profile)]) == (
        130 if failure == "interruption" else 1
    )
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err
    assert all(
        secret not in captured.err
        for secret in ["PRIVATE-PROVIDER", "PRIVATE-PROFILE", "I want backend development"]
    )
    assert count == stage + 1


@pytest.mark.parametrize("status", ["absent", "ambiguous"])
def test_unusable_posting_stops_later_stages(
    status: str,
    signed_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    posting = tmp_path / "posting.html"
    posting.write_text("No identified role")
    profile = profile_file(tmp_path)
    calls = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return completed(
            {
                "posting_status": status,
                "posting_explanation": "Target unavailable.",
                "arrangements": [],
                "home_working": [],
                "uncertainties": [],
                "conflicts": [],
            }
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **_kwargs: real_client(transport=httpx.MockTransport(handler))
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    assert main(["assess", str(posting), "--profile", str(profile)]) == 1
    assert not capsys.readouterr().out
    assert calls == [1]
