"""Acquisition limits and provenance are independent of inference."""

import hashlib

import pytest

from job_scan.retrieval import Document, RetrievalError, assemble_documents, validate_url


def test_assembled_evidence_preserves_content_and_provenance() -> None:
    source = assemble_documents(
        "https://careers.example/?job=42#selected",
        [
            Document("https://careers.example/redirect?job=42", "<h1>Careers</h1>"),
            Document("https://ats.example/job/42", "<h1>Engineer</h1><p>Fully remote</p>"),
        ],
    )
    assert source.path is None
    assert source.source_url == "https://careers.example/?job=42#selected"
    assert source.final_url == "https://careers.example/redirect?job=42"
    assert source.frame_urls == ["https://ats.example/job/42"]
    assert "<h1>Engineer</h1><p>Fully remote</p>" in source.html
    assert "https://ats.example/job/42" in source.html
    assert source.sha256 == hashlib.sha256(source.html.encode()).hexdigest()


@pytest.mark.parametrize("documents", [[], [Document("https://x.example", " ")]])
def test_unreadable_documents_fail(documents: list[Document]) -> None:
    with pytest.raises(RetrievalError, match="readable"):
        assemble_documents("https://x.example", documents)


def test_substantive_content_is_never_truncated() -> None:
    with pytest.raises(RetrievalError, match="256 KiB"):
        assemble_documents("https://x.example", [Document("https://x.example", "ä" * 131073)])


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/job",
        "https:///job",
        "https://user:secret@example.com/job",
        "https://x:bad",
        "https://x/\njob",
    ],
)
def test_invalid_url(url: str) -> None:
    with pytest.raises(ValueError):
        validate_url(url)


def test_job_selecting_url_is_unchanged() -> None:
    url = "https://example.com/jobs/?gh_jid=123&language=en#job-123"
    assert validate_url(url) == url


@pytest.mark.enable_socket
@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1"]
)
def test_browser_request_policy_rejects_private_addresses(address: str) -> None:
    import asyncio

    from job_scan.browser_network import public_address

    with pytest.raises(ValueError, match="public"):
        asyncio.run(public_address(address, 80))


@pytest.mark.enable_socket
@pytest.mark.parametrize("error", [TimeoutError(), RetrievalError("Unreadable frame")])
def test_retrieval_failures_explain_saved_html_fallback(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    from job_scan.retrieval import retrieve_posting

    async def failed(_url: str) -> None:
        raise error

    monkeypatch.setattr("job_scan.retrieval._retrieve", failed)
    with pytest.raises(RetrievalError, match=r"job-scan assess posting\.html"):
        retrieve_posting("https://example.com/job")


def test_url_input_adds_selection_and_availability_context_only_for_urls() -> None:
    import json

    from job_scan.ai import request_body

    file_request = json.loads(json.dumps(request_body("<h1>Engineer</h1>", "test")))
    url_request = json.loads(
        json.dumps(
            request_body("<h1>Engineer</h1>", "test", "https://example.com/?job=42#selected")
        )
    )
    assert "target_url" not in json.loads(str(file_request["input"][0]["content"]))
    assert json.loads(url_request["input"][0]["content"])["target_url"].endswith("?job=42#selected")
    assert "expired" in url_request["instructions"]
