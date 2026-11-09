"""External traffic is substituted at HTTPX's transport boundary only."""

import hashlib
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

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


def fictional_profile() -> dict[str, Any]:
    """Fresh fictional input; never reuse a personal preference file."""
    return {
        "schema_version": 1,
        "dimensions": {
            name: {"importance": 1, "preferences": "I want backend development."}
            for name in ("role_fit", "technology_fit", "field_interest", "company_affinity")
        },
    }


def fixed_rating(dimension_id: str = "role_fit", score: int = 80) -> dict[str, Any]:
    """Synthetic unit-test result, never a successful inference cassette."""
    return {
        "dimension_id": dimension_id,
        "status": "rated",
        "score": score,
        "explanation": "The stated responsibility matches the requested work.",
        "findings": [
            {
                "id": "work",
                "statement": "Backend development.",
                "evidence": [{"quote": "backend development", "occurrence": 0}],
            }
        ],
        "judgments": [
            {
                "preference_quote": "backend development",
                "finding_ids": ["work"],
                "polarity": "match",
                "explanation": "This matches the preference.",
            }
        ],
        "uncertainties": [],
        "conflicts": [],
    }


@pytest.fixture
def replay_sequence() -> Generator[list[Replay]]:
    """Assert every stage was consumed, including when an assertion fails."""
    replays: list[Replay] = []
    yield replays
    for replay in replays:
        assert not replay.exchanges, "Unconsumed HTTP exchanges"
