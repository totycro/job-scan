"""Synthetic failure cassettes; successful replay awaits actual provider recordings."""

from pathlib import Path

import httpx
import pytest

from job_scan.cli import main
from tests.conftest import Replay


@pytest.mark.parametrize("cassette", ["usage-limit", "incomplete", "invalid-evidence"])
def test_failed_inference(
    signed_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cassette: str,
) -> None:
    replay = Replay.load(Path("tests/recordings/inference") / f"{cassette}.json")
    real_client = httpx.Client

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(replay))

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    path = signed_session / "job.html"
    path.write_text("<h1>Engineer</h1><p>Fully remote</p>")
    assert main(["assess", str(path)]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err
    assert not replay.exchanges


def test_auth_and_catalog(
    signed_session: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers["authorization"].startswith("Bearer ")
        return httpx.Response(
            200,
            json={
                "models": [
                    {"slug": "test-model", "display_name": "Test Model", "visibility": "list"}
                ]
            },
        )

    def client(**_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(signed_session))
    assert main(["auth", "status"]) == 0
    assert "authorized" in capsys.readouterr().out
    assert main(["auth", "use", "test"]) == 0
    assert main(["models"]) == 0
    assert "test-model" in capsys.readouterr().out
    assert main(["auth", "logout"]) == 0
    assert main(["models"]) == 1
