"""Completion-gated subscription Responses transport; no API-key fallback.

Stream assembly/error boundaries adapted from fyntok revision 8b2f089.
"""

import json
import signal
import time
from collections.abc import Generator
from contextlib import contextmanager
from types import FrameType
from typing import Self

import httpx
from pydantic import BaseModel, Field, ValidationError

from job_scan.auth import RESOURCE, ChatGPTSession
from job_scan.criteria.work_arrangement import INSTRUCTIONS
from job_scan.models import WorkArrangementResult

DEFAULT_MODEL = "gpt-6.1-sol"


class RequestError(RuntimeError):
    """Diagnostics contain local text and safe status codes only."""


def http_failure(status: int) -> RequestError:
    message = {
        401: "ChatGPT sign-in was rejected. Sign in again.",
        403: "ChatGPT plan permission or account eligibility was denied.",
        429: "ChatGPT usage limit reached. Retry later.",
    }.get(status, "ChatGPT request failed.")
    return RequestError(f"{message} (HTTP {status})")


class Part(BaseModel):
    type: str
    text: str = ""


class Output(BaseModel):
    content: list[Part] = Field(default_factory=list)


class Completed(BaseModel):
    status: str = "completed"
    model: str | None = None
    output: list[Output] = Field(default_factory=list)


class Event(BaseModel):
    type: str
    response: Completed | None = None
    delta: str = ""
    text: str = ""
    output_index: int = 0
    content_index: int = 0


class CatalogModel(BaseModel):
    slug: str
    display_name: str
    visibility: str


class Catalog(BaseModel):
    models: list[CatalogModel]


@contextmanager
def deadline(seconds: float) -> Generator[None]:
    """Bound total synchronous I/O time, including a continuously active stream.

    The supported Unix CLI runs on the main thread. Restore any outer timer.
    """

    def expired(_signum: int, _frame: FrameType | None) -> None:
        raise RequestError("ChatGPT inference exceeded its total deadline.")

    previous = signal.signal(signal.SIGALRM, expired)
    started = time.monotonic()
    timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if timer[0]:
            signal.setitimer(
                signal.ITIMER_REAL, max(0.001, timer[0] - (time.monotonic() - started)), timer[1]
            )


def request_body(html: str, model: str) -> dict[str, object]:
    return {
        "model": model,
        "reasoning": {"effort": "low"},
        "instructions": INSTRUCTIONS,
        "input": [{"role": "user", "content": json.dumps({"html": html}, ensure_ascii=False)}],
        "store": False,
        "stream": True,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "work_arrangement",
                "strict": True,
                "schema": WorkArrangementResult.model_json_schema(),
            }
        },
    }


class ResponsesClient:
    def __init__(self, session: ChatGPTSession, client: httpx.Client | None = None) -> None:
        self.session = session
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(180, connect=10), follow_redirects=False
        )
        self.returned_model: str | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.client.close()

    def models(self) -> list[CatalogModel]:
        try:
            response = self.client.get(
                RESOURCE + "/models",
                headers={
                    "Authorization": "Bearer " + self.session.access_token(),
                },
            )
            if not response.is_success:
                raise http_failure(response.status_code)
            return [
                m
                for m in Catalog.model_validate_json(response.content).models
                if m.visibility == "list"
            ]
        except httpx.HTTPError, ValidationError:
            raise RequestError("Unable to read ChatGPT model catalog.") from None

    def assess_html(self, html: str, model: str = DEFAULT_MODEL) -> WorkArrangementResult:
        self.returned_model = None
        active = self.session.load().active
        token = self.session.access_token()
        try:
            with (
                deadline(180),
                self.client.stream(
                    "POST",
                    RESOURCE + "/responses",
                    json=request_body(html, model),
                    headers={"Authorization": "Bearer " + token},
                ) as response,
            ):
                if not response.is_success:
                    raise http_failure(response.status_code)
                text, returned_model = self.read_stream(response)
            # Do not accept a response after sign-out or registration changes.
            if self.session.load().active != active:
                raise RequestError("ChatGPT registration changed during inference.")
            self.session.access_token()
            result = WorkArrangementResult.model_validate_json(text)
            self.returned_model = returned_model
            return result
        except httpx.HTTPError, ValueError:
            raise RequestError(
                "ChatGPT returned invalid output or the connection failed."
            ) from None

    @staticmethod
    def read_stream(response: httpx.Response) -> tuple[str, str | None]:
        completed: Completed | None = None
        streamed: dict[tuple[int, int], str] = {}
        refused = False
        for line in response.iter_lines():
            if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                continue
            event = Event.model_validate_json(line[5:])
            if event.type in {"response.failed", "response.incomplete", "error"}:
                raise RequestError("ChatGPT inference failed or was incomplete; check plan usage.")
            if event.type.startswith("response.refusal."):
                refused = True
            key = (event.output_index, event.content_index)
            if event.type == "response.output_text.delta":
                streamed[key] = streamed.get(key, "") + event.delta
            elif event.type == "response.output_text.done":
                streamed[key] = event.text
            elif event.type == "response.completed":
                completed = event.response
        if completed is None or completed.status != "completed":
            raise RequestError("ChatGPT stream ended without successful completion.")
        parts = [p for item in completed.output for p in item.content]
        if refused or any(p.type == "refusal" for p in parts):
            raise RequestError("ChatGPT declined to assess this posting.")
        text = "".join(p.text for p in parts if p.type == "output_text")
        text = text or "".join(streamed[k] for k in sorted(streamed))
        if not text.strip():
            raise RequestError("ChatGPT completed without assessment output.")
        return text, completed.model
