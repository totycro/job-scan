"""ChatGPT OAuth lifecycle, adapted from fyntok revision 8b2f089.

Only generic registration/PKCE/storage/refresh concepts are reused. Job-scan owns
its app identity and store. All HTTP, including JWKS, uses one injectable client.
"""

import base64
import fcntl
import hashlib
import os
import secrets
import tempfile
import time
import webbrowser
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Self, override
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4

import httpx
import jwt
from pydantic import BaseModel, ConfigDict, Field, ValidationError

RESOURCE = "https://api.openai.com/v1"
ISSUER = "https://auth.openai.com"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
DISCOVERY = ISSUER + "/.well-known/openid-configuration"
PERMISSION = "chatgpt.tokens.use.direct"


class Account(BaseModel):
    client_id: str
    subject: str
    label: str
    access_token: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: float = 0


class Store(BaseModel):
    host_id: str = Field(default_factory=lambda: "urn:uuid:" + str(uuid4()))
    accounts: dict[str, Account] = Field(default_factory=dict)
    active: str | None = None
    retry_client_id: str | None = None


class Tokens(BaseModel):
    access_token: str
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None
    expires_in: int = 3600


class OAuthFailure(BaseModel):
    error: str


class Pending(BaseModel):
    state: str
    nonce: str
    verifier: str
    redirect: str
    created: float
    client_id: str | None
    subject: str | None


class Discovery(BaseModel):
    issuer: str
    jwks_uri: str
    revocation_endpoint: str | None = None


class Claims(BaseModel):
    sub: str
    nonce: str
    email: str | None = None


class Key(BaseModel):
    model_config = ConfigDict(extra="allow")
    kid: str
    kty: str


class Keys(BaseModel):
    keys: list[Key]


class ChatGPTSession:
    def __init__(self, directory: Path | None = None, client: httpx.Client | None = None) -> None:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        self.directory = directory or root / "job-scan"
        self.path = self.directory / "accounts.json"
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.pending: Pending | None = None
        self.login_error: str | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.client.close()

    @contextmanager
    def locked(self) -> Generator[None]:
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        with (self.directory / "session.lock").open("a") as lock:
            Path(lock.name).chmod(0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def load(self) -> Store:
        return Store.model_validate_json(self.path.read_bytes()) if self.path.exists() else Store()

    def save(self, store: Store) -> None:
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, "w") as out:
                out.write(store.model_dump_json())
                out.flush()
                os.fsync(out.fileno())
            Path(name).replace(self.path)
        finally:
            Path(name).unlink(missing_ok=True)

    def status(self) -> list[str]:
        with self.locked():
            data = self.load()
            lines = []
            for cid, account in data.accounts.items():
                state = "signed out"
                if account.access_token is not None and PERMISSION in account.scopes:
                    state = "authorized" if account.expires_at > time.time() else "refresh required"
                marker = "*" if cid == data.active else "-"
                lines.append(f"{marker} {account.label} · {cid} ({state})")
            return lines

    def select(self, client_id: str) -> None:
        with self.locked():
            data = self.load()
            if client_id not in data.accounts:
                raise ValueError("Unknown ChatGPT registration.")
            data.active = client_id
            self.save(data)

    def begin(self, redirect: str, client_id: str | None = None) -> str:
        with self.locked():
            if self.pending:
                raise ValueError("A sign-in is already in progress.")
            data = self.load()
            client_id = client_id or data.retry_client_id
            prior = data.accounts.get(client_id or "")
            if client_id is not None and not prior and client_id != data.retry_client_id:
                raise ValueError("Unknown ChatGPT registration.")
            self.save(data)
            p = Pending(
                state=secrets.token_urlsafe(32),
                nonce=secrets.token_urlsafe(32),
                verifier=secrets.token_urlsafe(48),
                redirect=redirect,
                created=time.time(),
                client_id=client_id,
                subject=prior.subject if prior else None,
            )
            self.pending = p
            self.login_error = None
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(p.verifier.encode()).digest(), padded=False
            )
            params = {
                "client_id": client_id or "dynamic_agent_client",
                "ext_agent_host_id": data.host_id,
                "response_type": "code",
                "redirect_uri": redirect,
                "scope": "openid profile email offline_access resource.invoke " + PERMISSION,
                "resource": RESOURCE,
                "state": p.state,
                "nonce": p.nonce,
                "code_challenge_method": "S256",
                "code_challenge": challenge.decode("ascii"),
            }
            if client_id is None:
                params["agent_name_hint"] = "job-scan"
            return ISSUER + "/api/accounts/authorize?" + urlencode(params)

    def metadata(self) -> Discovery:
        response = self.client.get(DISCOVERY)
        response.raise_for_status()
        metadata = Discovery.model_validate_json(response.content)
        if metadata.issuer != ISSUER or not metadata.jwks_uri.startswith(ISSUER + "/"):
            raise ValueError("Unexpected OpenID provider.")
        return metadata

    def verify_identity(self, token: str, cid: str) -> Claims:
        metadata = self.metadata()
        response = self.client.get(metadata.jwks_uri)
        response.raise_for_status()
        keys = Keys.model_validate_json(response.content)
        header = jwt.get_unverified_header(token)
        key = next((k for k in keys.keys if k.kid == header.get("kid")), None)
        if key is None:
            raise ValueError("Signing key unavailable.")
        public_key = jwt.PyJWK.from_dict(key.model_dump()).key
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=cid,
            issuer=ISSUER,
            options={"require": ["exp", "iss", "aud", "sub", "nonce"]},
        )
        return Claims.model_validate(decoded)

    def complete(self, callback: str) -> None:
        with self.locked():
            p = self.pending
            if not p:
                raise ValueError("No pending sign-in.")
            parsed = urlparse(callback)
            if parsed._replace(query="", fragment="").geturl() != p.redirect:
                raise ValueError("Unexpected callback URI.")
            query = parse_qs(parsed.query, keep_blank_values=True)
            if any(len(v) != 1 for v in query.values()):
                raise ValueError("Duplicate callback parameters.")
            values = {k: v[0] for k, v in query.items()}
            if not secrets.compare_digest(values.get("state", ""), p.state):
                raise ValueError("OAuth state mismatch.")
            self.pending = None
            if time.time() - p.created > 900 or "error" in values:
                raise ValueError("Sign-in expired, declined, or failed.")
            cid = values.get("client_id") or p.client_id
            if (
                cid is None
                or cid == "dynamic_agent_client"
                or (p.client_id is not None and cid != p.client_id)
            ):
                raise ValueError("Invalid issued client ID.")
            if not values.get("code", ""):
                raise ValueError("Missing authorization code.")
            data = self.load()
            if p.client_id is None or cid == data.retry_client_id:
                data.retry_client_id = cid
                self.save(data)
            response = self.client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": cid,
                    "code": values["code"],
                    "code_verifier": p.verifier,
                    "redirect_uri": p.redirect,
                    "resource": RESOURCE,
                },
            )
            response.raise_for_status()
            tokens = Tokens.model_validate_json(response.content)
            if tokens.id_token is None:
                raise ValueError("Missing identity token.")
            claims = self.verify_identity(tokens.id_token, cid)
            if not secrets.compare_digest(claims.nonce, p.nonce) or (
                p.subject is not None and claims.sub != p.subject
            ):
                raise ValueError("Sign-in identity or nonce mismatch.")
            prior = data.accounts.get(cid)
            if prior and prior.subject != claims.sub:
                raise ValueError("Registration belongs to another account.")
            data.accounts[cid] = Account(
                client_id=cid,
                subject=claims.sub,
                label=claims.email or claims.sub,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                id_token=tokens.id_token,
                scopes=(tokens.scope or "").split(),
                expires_at=time.time() + tokens.expires_in,
            )
            data.active = cid
            data.retry_client_id = None
            self.save(data)

    def access_token(self) -> str:
        with self.locked():
            data = self.load()
            record = data.accounts.get(data.active or "")
            if not record or record.access_token is None:
                raise RuntimeError("Sign in with ChatGPT first: job-scan auth login.")
            if PERMISSION not in record.scopes:
                raise RuntimeError("ChatGPT plan permission has not been granted.")
            if record.expires_at <= time.time() + 60:
                if record.refresh_token is None:
                    raise RuntimeError("Session expired. Sign in again.")
                response = self.client.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": record.refresh_token,
                        "client_id": record.client_id,
                        "resource": RESOURCE,
                    },
                )
                if response.is_error:
                    try:
                        code = OAuthFailure.model_validate_json(response.content).error
                    except ValidationError:
                        code = "unknown"
                    if code in {
                        "invalid_grant",
                        "refresh_token_expired",
                        "refresh_token_invalidated",
                        "refresh_token_reused",
                    }:
                        record.access_token = record.refresh_token = record.id_token = None
                        self.save(data)
                        raise RuntimeError("Session expired or revoked. Sign in again.")
                response.raise_for_status()
                tokens = Tokens.model_validate_json(response.content)
                record.access_token = tokens.access_token
                record.refresh_token = tokens.refresh_token or record.refresh_token
                record.id_token = tokens.id_token or record.id_token
                if tokens.scope is not None:
                    record.scopes = tokens.scope.split()
                record.expires_at = time.time() + tokens.expires_in
                self.save(data)
                if PERMISSION not in record.scopes:
                    raise RuntimeError("ChatGPT plan permission is no longer granted.")
            return record.access_token

    def sign_out(self) -> bool:
        with self.locked():
            data = self.load()
            record = data.accounts.get(data.active or "")
            if not record:
                return True
            confirmed = record.refresh_token is None
            try:
                if record.refresh_token is not None:
                    endpoint = self.metadata().revocation_endpoint
                    if endpoint is None or not endpoint.startswith(ISSUER + "/"):
                        raise ValueError("Unexpected revocation endpoint.")
                    response = self.client.post(
                        endpoint,
                        data={
                            "token": record.refresh_token,
                            "token_type_hint": "refresh_token",
                            "client_id": record.client_id,
                        },
                    )
                    confirmed = response.status_code == 200
            except httpx.HTTPError, ValueError:
                confirmed = False
            finally:
                record.access_token = record.refresh_token = record.id_token = None
                self.save(data)
            return confirmed

    def login(self, client_id: str | None = None) -> None:
        owner = self

        class Callback(BaseHTTPRequestHandler):
            @override
            def log_message(self, format: str, *args: object) -> None:
                pass  # Never log callback authorization codes.

            def do_GET(self) -> None:
                if urlparse(self.path).path != "/auth/callback":
                    self.send_error(404)
                    return
                try:
                    owner.complete(redirect + "?" + urlparse(self.path).query)
                    message, status = "Sign-in complete. Return to job-scan.", 200
                except ValueError, RuntimeError, httpx.HTTPError, jwt.PyJWTError:
                    owner.pending = None
                    owner.login_error = "Sign-in failed. Try again."
                    message, status = owner.login_error, 400
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(message.encode())

        with HTTPServer(("127.0.0.1", 0), Callback) as server:
            redirect = f"http://127.0.0.1:{server.server_port}/auth/callback"
            url = self.begin(redirect, client_id)
            print("Continue with ChatGPT:\n" + url, flush=True)
            webbrowser.open(url)
            deadline = time.monotonic() + 900
            server.timeout = 0.5
            try:
                while self.pending and time.monotonic() < deadline:
                    server.handle_request()
                if self.pending:
                    raise RuntimeError("Sign-in timed out after 15 minutes.")
                if self.login_error is not None:
                    raise RuntimeError(self.login_error)
            finally:
                self.pending = None
