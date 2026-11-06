"""External traffic is substituted at HTTPX's transport boundary only."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest


class Replay:
    """Strict, ordered request matching for synthetic or sanitized cassettes."""

    def __init__(self, exchanges: list[dict[str, object]]) -> None:
        self.exchanges = list(exchanges)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert self.exchanges, f"Unexpected request: {request.method} {request.url}"
        exchange = self.exchanges.pop(0)
        assert request.method == exchange["method"]
        assert str(request.url) == exchange["url"]
        assert hashlib.sha256(request.content).hexdigest() == exchange["request_sha256"]
        return httpx.Response(int(str(exchange["status"])), content=str(exchange["body"]).encode())

    @classmethod
    def load(cls, path: Path) -> Replay:
        return cls(json.loads(path.read_text())["exchanges"])


@pytest.fixture
def remote_result() -> dict[str, object]:
    return {
        "posting_status": "identified",
        "posting_explanation": None,
        "arrangements": [
            {
                "kind": "remote",
                "context": "Engineer",
                "evidence": [{"quote": "Fully remote", "occurrence": 0}],
            }
        ],
        "home_working": [],
        "uncertainties": [],
        "conflicts": [],
    }


@pytest.fixture
def signed_session(tmp_path: Path) -> Path:
    from job_scan.auth import PERMISSION, Account, ChatGPTSession

    session = ChatGPTSession(tmp_path / "job-scan")
    store = session.load()
    synthetic = "test-only-not-a-real-credential"
    store.accounts["test"] = Account(
        client_id="test",
        subject="synthetic-user",
        label="Synthetic user",
        access_token=synthetic,
        scopes=[PERMISSION],
        expires_at=10**12,
    )
    store.active = "test"
    with session.locked():
        session.save(store)
    session.client.close()
    return tmp_path
