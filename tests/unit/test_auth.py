import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from job_scan.auth import PERMISSION, Account, ChatGPTSession


def test_registration_storage_and_permission(tmp_path: Path) -> None:
    session = ChatGPTSession(tmp_path)
    url = session.begin("http://127.0.0.1:1234/auth/callback")
    params = parse_qs(urlparse(url).query)
    assert params["agent_name_hint"] == ["job-scan"]
    assert params["code_challenge_method"] == ["S256"]
    assert session.load().host_id == params["ext_agent_host_id"][0]
    with pytest.raises(ValueError, match="progress"):
        session.begin("http://127.0.0.1/x")
    with pytest.raises(ValueError, match="state"):
        session.complete("http://127.0.0.1:1234/auth/callback?state=wrong")
    session.pending = None
    with pytest.raises(ValueError, match="Unknown"):
        session.begin("http://127.0.0.1/x", "unknown")
    data = session.load()
    data.accounts["test"] = Account(client_id="test", subject="synthetic", label="Test")
    data.active = "test"
    session.save(data)
    session.select("test")
    assert session.status() == ["* Test · test (signed out)"]
    assert session.path.stat().st_mode & 0o777 == 0o600
    assert tmp_path.stat().st_mode & 0o777 == 0o700
    with pytest.raises(RuntimeError, match="Sign in"):
        session.access_token()
    assert session.sign_out()
    with pytest.raises(ValueError, match="Unknown"):
        session.select("nope")


def test_access_and_refresh(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/token")
        return httpx.Response(200, json={"access_token": "new", "expires_in": 3600})

    session = ChatGPTSession(tmp_path, httpx.Client(transport=httpx.MockTransport(handler)))
    data = session.load()
    account = Account(
        client_id="test",
        subject="test",
        label="Test",
        access_token="synthetic",  # noqa: S106 - deliberately fake test credential.
        scopes=[PERMISSION],
        expires_at=time.time() + 3600,
    )
    data.accounts["test"] = account
    data.active = "test"
    session.save(data)
    assert session.access_token() == "synthetic"
    account.expires_at = 0
    account.refresh_token = "synthetic-refresh"  # noqa: S105 - fake refresh credential.
    session.save(data)
    assert session.access_token() == "new"
    account.scopes = []
    session.save(data)
    with pytest.raises(RuntimeError, match="permission"):
        session.access_token()


def test_signed_oidc_login(tmp_path: Path) -> None:
    import base64
    import json
    from urllib.parse import urlencode

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from job_scan.auth import DISCOVERY, ISSUER, TOKEN_URL

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private.public_key().public_numbers()

    def encode_number(number: int) -> str:
        return (
            base64.urlsafe_b64encode(number.to_bytes((number.bit_length() + 7) // 8, "big"))
            .decode()
            .rstrip("=")
        )

    jwk = {
        "kid": "test",
        "kty": "RSA",
        "n": encode_number(numbers.n),
        "e": encode_number(numbers.e),
    }
    current = {"nonce": "", "scope": PERMISSION, "subject": "synthetic-user"}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            claims = {
                "sub": current["subject"],
                "nonce": current["nonce"],
                "iss": ISSUER,
                "aud": "issued",
                "exp": time.time() + 3600,
            }
            encoded = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test"})
            return httpx.Response(
                200,
                json={
                    "access_token": "synthetic",
                    "id_token": encoded,
                    "scope": current["scope"],
                    "expires_in": 3600,
                },
            )
        if str(request.url) == DISCOVERY:
            return httpx.Response(
                200,
                json=json.loads(Path("tests/recordings/auth/discovery.json").read_text())[
                    "response"
                ],
            )
        return httpx.Response(200, json={"keys": [jwk]})

    session = ChatGPTSession(tmp_path, httpx.Client(transport=httpx.MockTransport(handler)))
    redirect = "http://127.0.0.1:1234/auth/callback"
    session.begin(redirect)
    assert session.pending is not None
    current["nonce"] = session.pending.nonce
    callback = (
        redirect
        + "?"
        + urlencode({"state": session.pending.state, "code": "fake", "client_id": "issued"})
    )
    session.complete(callback)
    assert session.access_token() == "synthetic"
    assert session.load().retry_client_id is None
    # Returning registration reuses the client ID and omits a new agent-name hint.
    url = session.begin(redirect, "issued")
    assert "agent_name_hint" not in url
    assert session.pending is not None
    current["nonce"] = "wrong-nonce"
    with pytest.raises(ValueError, match="nonce"):
        session.complete(
            redirect + "?" + urlencode({"state": session.pending.state, "code": "fake"})
        )
    session.begin(redirect, "issued")
    assert session.pending is not None
    current["nonce"] = session.pending.nonce
    current["subject"] = "different-user"
    with pytest.raises(ValueError, match="identity"):
        session.complete(
            redirect + "?" + urlencode({"state": session.pending.state, "code": "fake"})
        )
    session.begin(redirect, "issued")
    assert session.pending is not None
    current["nonce"] = session.pending.nonce
    current["subject"] = "synthetic-user"
    current["scope"] = "openid"
    session.complete(redirect + "?" + urlencode({"state": session.pending.state, "code": "fake"}))
    with pytest.raises(RuntimeError, match="permission"):
        session.access_token()


@pytest.mark.parametrize(
    "suffix, message",
    [
        ("?state=x&state=y", "Duplicate"),
        ("?state=STATE&error=access_denied", "declined"),
        ("?state=STATE&code=x", "client ID"),
        ("?state=STATE&client_id=issued", "authorization code"),
        ("?state=STATE&client_id=dynamic_agent_client&code=x", "client ID"),
    ],
)
def test_callback_rejections(tmp_path: Path, suffix: str, message: str) -> None:
    session = ChatGPTSession(tmp_path)
    redirect = "http://127.0.0.1:1234/auth/callback"
    session.begin(redirect)
    assert session.pending is not None
    with pytest.raises(ValueError, match=message):
        session.complete(redirect + suffix.replace("STATE", session.pending.state))


def test_callback_missing_attempt_uri_expiry(tmp_path: Path) -> None:
    session = ChatGPTSession(tmp_path)
    with pytest.raises(ValueError, match="pending"):
        session.complete("http://localhost")
    session.begin("http://127.0.0.1:1234/auth/callback")
    assert session.pending is not None
    with pytest.raises(ValueError, match="URI"):
        session.complete("http://different/callback")
    session.pending.created = 0
    state = session.pending.state
    with pytest.raises(ValueError, match="expired"):
        session.complete("http://127.0.0.1:1234/auth/callback?state=" + state)


@pytest.mark.parametrize("status", [200, 400, 500])
def test_refresh_and_revocation(tmp_path: Path, status: int) -> None:
    from job_scan.auth import DISCOVERY, ISSUER

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == DISCOVERY:
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "jwks_uri": ISSUER + "/keys",
                    "revocation_endpoint": ISSUER + "/revoke",
                },
            )
        if request.url.path.endswith("/revoke"):
            return httpx.Response(status)
        return httpx.Response(
            status,
            json={
                "access_token": "synthetic",
                "scope": "openid",
                "error": "invalid_grant" if status == 400 else "server_error",
            },
        )

    session = ChatGPTSession(tmp_path, httpx.Client(transport=httpx.MockTransport(handler)))
    synthetic = "not-a-real-token"
    store = session.load()
    store.accounts["test"] = Account(
        client_id="test",
        subject="test",
        label="Test",
        access_token=synthetic,
        refresh_token=synthetic,
        scopes=[PERMISSION],
        expires_at=0,
    )
    store.active = "test"
    session.save(store)
    assert "refresh required" in session.status()[0]
    if status == 500:
        with pytest.raises(httpx.HTTPStatusError):
            session.access_token()
        assert session.load().accounts["test"].access_token == synthetic
    else:
        with pytest.raises(RuntimeError):
            session.access_token()
    assert session.sign_out() == (status != 500)
    assert session.load().accounts["test"].access_token is None
    assert session.load().accounts["test"].client_id == "test"


def test_expired_without_refresh(tmp_path: Path) -> None:
    session = ChatGPTSession(tmp_path)
    store = session.load()
    synthetic = "not-real"
    store.accounts["x"] = Account(
        client_id="x", subject="x", label="x", access_token=synthetic, scopes=[PERMISSION]
    )
    store.active = "x"
    session.save(store)
    with pytest.raises(RuntimeError, match="expired"):
        session.access_token()


def test_bad_metadata_and_revocation(tmp_path: Path) -> None:
    for metadata in (
        {"issuer": "https://wrong", "jwks_uri": "https://wrong/keys"},
        {
            "issuer": "https://auth.openai.com",
            "jwks_uri": "https://auth.openai.com/keys",
            "revocation_endpoint": "https://untrusted/revoke",
        },
    ):
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda _r, value=metadata: httpx.Response(200, json=value)
            )
        )
        session = ChatGPTSession(tmp_path, client)
        synthetic = "not-real"
        store = session.load()
        store.accounts["x"] = Account(
            client_id="x",
            subject="x",
            label="x",
            access_token=synthetic,
            refresh_token=synthetic,
            scopes=[PERMISSION],
        )
        store.active = "x"
        session.save(store)
        assert not session.sign_out()
        assert session.load().accounts["x"].refresh_token is None


@pytest.mark.parametrize("mode", ["success", "failed", "timeout", "interrupt"])
def test_foreground_login(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    from typing import Self

    import job_scan.auth as auth

    session = ChatGPTSession(tmp_path)

    class Server:
        server_port = 1234
        timeout = 0.0

        def __init__(self, _address: object, _handler: object) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def handle_request(self) -> None:
            if mode == "interrupt":
                raise KeyboardInterrupt
            session.pending = None
            if mode == "failed":
                session.login_error = "Sign-in failed."

    monkeypatch.setattr(auth, "HTTPServer", Server)
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: True)
    ticks = iter([0.0, 1000.0])
    if mode == "timeout":
        monkeypatch.setattr(auth.time, "monotonic", lambda: next(ticks))
    if mode == "success":
        session.login()
    else:
        error = KeyboardInterrupt if mode == "interrupt" else RuntimeError
        with pytest.raises(error):
            session.login()
    assert session.pending is None


def test_callback_http_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    from http.server import BaseHTTPRequestHandler
    from typing import Protocol, Self, cast
    from unittest.mock import Mock

    import job_scan.auth as auth

    session = ChatGPTSession(tmp_path)
    statuses = []

    class GetHandler(Protocol):
        def do_GET(self) -> None: ...

    class Server:
        server_port = 1234
        timeout = 0.0

        def __init__(self, _address: object, handler: type[BaseHTTPRequestHandler]) -> None:
            self.handler = handler

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def handle_request(self) -> None:
            callback = self.handler.__new__(self.handler)
            callback.wfile = io.BytesIO()
            callback.send_error = Mock()
            callback.send_response = Mock()
            callback.send_header = Mock()
            callback.end_headers = Mock()
            callback.path = "/unknown"
            callback.log_message("hidden")
            cast("GetHandler", callback).do_GET()
            callback.send_error.assert_called_once_with(404)
            callback.path = "/auth/callback?state=wrong"
            cast("GetHandler", callback).do_GET()
            statuses.append(callback.send_response.call_args.args[0])

    monkeypatch.setattr(auth, "HTTPServer", Server)
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: True)
    with pytest.raises(RuntimeError, match="failed"):
        session.login()
    assert statuses == [400]


def test_refresh_configuration_error_keeps_session(signed_session: Path) -> None:
    session = ChatGPTSession(
        signed_session / "job-scan",
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _r: httpx.Response(400, json={"error": "invalid_client"})
            )
        ),
    )
    store = session.load()
    account = store.accounts["test"]
    account.expires_at = 0
    account.refresh_token = account.access_token
    session.save(store)
    with pytest.raises(httpx.HTTPStatusError):
        session.access_token()
    assert session.load().accounts["test"].refresh_token is not None
