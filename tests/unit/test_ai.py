import json
from pathlib import Path

import httpx
import pytest

from job_scan.ai import ResponsesClient
from job_scan.auth import PERMISSION, Account, ChatGPTSession


def test_stream_completion_and_failures(tmp_path: Path, remote_result: dict[str, object]) -> None:
    session = ChatGPTSession(tmp_path)
    data = session.load()
    data.accounts["test"] = Account(
        client_id="test",
        subject="test",
        label="Test",
        access_token="synthetic",  # noqa: S106 - deliberately fake test credential.
        scopes=[PERMISSION],
        expires_at=10**12,
    )
    data.active = "test"
    session.save(data)
    for event, ok in (
        ("response.completed", True),
        ("response.failed", False),
        ("response.incomplete", False),
        ("response.refusal.done", False),
        ("response.output_text.done", False),
    ):

        def handler(request: httpx.Request, event_type: str = event) -> httpx.Response:
            body = json.loads(request.content)
            assert body["store"] is False
            assert body["stream"] is True
            assert body["reasoning"] == {"effort": "low"}
            response = {
                "status": "completed",
                "model": "gpt-6.1-sol",
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(remote_result)}]}
                ],
            }
            return httpx.Response(
                200,
                text="data: "
                + json.dumps(
                    {
                        "type": event_type,
                        "response": response,
                    }
                )
                + "\n\n",
            )

        ai = ResponsesClient(session, httpx.Client(transport=httpx.MockTransport(handler)))
        if ok:
            assert ai.assess_html("Fully remote").arrangements[0].kind == "remote"
        else:
            with pytest.raises(RuntimeError):
                ai.assess_html("Fully remote")


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_http_errors(signed_session: Path, status: int) -> None:
    from job_scan.ai import RequestError

    session = ChatGPTSession(signed_session / "job-scan")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _r: httpx.Response(status, text="secret"))
    )
    ai = ResponsesClient(session, client)
    with pytest.raises(RequestError, match="HTTP") as error:
        ai.assess_html("Fully remote")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        '{"models":[]}',
        '{"models":[{"slug":"x","display_name":"X","visibility":"list"},'
        '{"slug":"y","display_name":"Y","visibility":"hidden"}]}',
    ],
)
def test_catalog(signed_session: Path, body: str) -> None:
    session = ChatGPTSession(signed_session / "job-scan")
    with ResponsesClient(
        session,
        httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200, text=body))),
    ) as ai:
        if body == "not json":
            with pytest.raises(RuntimeError, match="catalog"):
                ai.models()
        else:
            assert [m.slug for m in ai.models()] == ([] if body == '{"models":[]}' else ["x"])


@pytest.mark.parametrize(
    "events,success",
    [
        ([{"type": "response.completed", "response": {"output": []}}], False),
        ([{"type": "response.completed", "response": {"status": "incomplete"}}], False),
        (
            [
                {
                    "type": "response.completed",
                    "response": {"output": [{"content": [{"type": "refusal"}]}]},
                }
            ],
            False,
        ),
        (
            [
                {"type": "response.output_text.delta", "delta": "{"},
                {"type": "response.output_text.delta", "delta": "}"},
                {"type": "response.completed", "response": {}},
            ],
            True,
        ),
        (
            [
                {"type": "response.output_text.delta", "delta": "ignored"},
                {"type": "response.output_text.done", "text": "{}"},
                {"type": "response.completed", "response": {}},
            ],
            True,
        ),
        ([{"type": "error"}], False),
    ],
)
def test_assembly(events: list[dict[str, object]], success: bool) -> None:
    response = httpx.Response(
        200,
        text=": comment\n\ndata: [DONE]\n"
        + "".join("data: " + json.dumps(e) + "\n\n" for e in events),
    )
    if success:
        assert ResponsesClient.read_stream(response)[0] == "{}"
    else:
        with pytest.raises(RuntimeError):
            ResponsesClient.read_stream(response)


def test_malformed_and_network(signed_session: Path) -> None:
    session = ChatGPTSession(signed_session / "job-scan")
    for response in (
        httpx.Response(200, text="data: broken\n\n"),
        httpx.Response(
            200,
            text='data: {"type":"response.completed","response":{'
            '"output":[{"content":[{"type":"output_text","text":"{}"}]}]}}\n\n',
        ),
    ):
        ai = ResponsesClient(
            session, httpx.Client(transport=httpx.MockTransport(lambda _r, value=response: value))
        )
        with pytest.raises(RuntimeError, match="invalid"):
            ai.assess_html("job")

    def failure(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret")

    with ResponsesClient(session, httpx.Client(transport=httpx.MockTransport(failure))) as ai:
        with pytest.raises(RuntimeError, match="connection"):
            ai.assess_html("job")
        with pytest.raises(RuntimeError, match="catalog"):
            ai.models()


def test_deadline() -> None:
    import signal
    import time

    from job_scan.ai import deadline

    original = signal.getsignal(signal.SIGALRM)
    with pytest.raises(RuntimeError, match="deadline"), deadline(0.01):
        time.sleep(0.02)
    assert signal.getsignal(signal.SIGALRM) == original
    with deadline(1), deadline(0.1):
        pass


def test_changed_registration_rejects_result(
    signed_session: Path, remote_result: dict[str, object]
) -> None:
    session = ChatGPTSession(signed_session / "job-scan")

    def handler(_request: httpx.Request) -> httpx.Response:
        with session.locked():
            store = session.load()
            store.active = None
            session.save(store)
        return httpx.Response(
            200,
            text="data: "
            + json.dumps(
                {
                    "type": "response.completed",
                    "response": {
                        "output": [
                            {
                                "content": [
                                    {"type": "output_text", "text": json.dumps(remote_result)}
                                ]
                            }
                        ]
                    },
                }
            )
            + "\n\n",
        )

    with (
        ResponsesClient(session, httpx.Client(transport=httpx.MockTransport(handler))) as ai,
        pytest.raises(RuntimeError, match="registration changed"),
    ):
        ai.assess_html("Fully remote")


def test_catalog_status(signed_session: Path) -> None:
    session = ChatGPTSession(signed_session / "job-scan")
    with (
        ResponsesClient(
            session, httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(403)))
        ) as ai,
        pytest.raises(RuntimeError, match="HTTP 403"),
    ):
        ai.models()
