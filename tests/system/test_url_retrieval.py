"""Real Chromium, with all browser HTTP replaced by deterministic authored pages."""

import asyncio

import pytest
from playwright.async_api import Route, async_playwright

from job_scan.evidence import resolve
from job_scan.models import Evidence
from job_scan.retrieval import RetrievalError, acquire


@pytest.fixture
def virtual_settling_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Advance Python's settling clock for pages with no delayed content.

    Keep Chromium and its event loop on real time. The delayed-rendering cases
    deliberately omit this fixture so they exercise the real settling window.
    """
    from job_scan import retrieval

    class Clock:
        elapsed = 0.0

        def get_running_loop(self) -> Clock:
            return self

        def time(self) -> float:
            return self.elapsed

        async def sleep(self, delay: float) -> None:
            self.elapsed += delay
            await asyncio.sleep(0)

    monkeypatch.setattr(retrieval, "asyncio", Clock())


@pytest.mark.enable_socket
@pytest.mark.parametrize("framed", [False, True])
def test_rendered_selection_and_frame_evidence(framed: bool) -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context(service_workers="block")
                requests = []

                async def route(request: Route) -> None:
                    requests.append(request.request.url)
                    if request.request.url == "https://jobs.example/careers?job=42":
                        script = (
                            "document.body.innerHTML = '<h1>Engineer 42</h1><p>Fully remote</p>'"
                            if not framed
                            else "document.body.innerHTML = '<iframe src=\"https://ats.example/job/42\"></iframe>'"
                        )
                        await request.fulfill(
                            content_type="text/html",
                            body=(
                                "<body><p>Loading</p><script>"
                                "if (location.hash !== '#selected') throw Error('selection lost');"
                                f"setTimeout(() => {{{script}}}, 500);</script></body>"
                            ),
                        )
                    elif request.request.url == "https://ats.example/job/42":
                        await request.fulfill(
                            content_type="text/html",
                            body="<h1>Engineer 42</h1><p>Fully remote</p><script>"
                            + "x" * 300000
                            + "</script>",
                        )
                    else:
                        await request.abort()
                        pytest.fail(f"Unrecorded browser request: {request.request.url}")

                await context.route("**/*", route)
                source = await acquire(
                    await context.new_page(), "https://jobs.example/careers?job=42#selected"
                )
                assert "Engineer 42" in source.html
                assert "Loading" not in source.html
                assert "<script>" not in source.html
                assert source.source_url == "https://jobs.example/careers?job=42#selected"
                evidence = resolve(source.html, Evidence(quote="Fully remote", occurrence=0))
                assert source.html[evidence.start : evidence.end] == "Fully remote"
                assert source.frame_urls == (["https://ats.example/job/42"] if framed else [])
                assert "https://jobs.example/careers?job=42" in requests
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.parametrize("status", [403, 404, 410])
def test_unavailable_posting_is_not_assessed(status: int) -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def blocked(route: Route) -> None:
                    await route.fulfill(status=status, body="Unavailable")

                await context.route("**/*", blocked)
                with pytest.raises(RetrievalError, match="blocked or unavailable"):
                    await acquire(await context.new_page(), "https://jobs.example/42")
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.usefixtures("virtual_settling_clock")
def test_structured_head_and_shadow_content_survive() -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def fixture(route: Route) -> None:
                    await route.fulfill(
                        content_type="text/html",
                        body="""<head><script type="application/ld+json">
                        {"@type":"JobPosting","title":"Engineer 42"}</script></head>
                        <body><job-details></job-details><script>
                        const element = document.querySelector('job-details');
                        element.attachShadow({mode:'open'}).innerHTML =
                            '<h1>Engineer 42</h1><p>Fully remote</p>';
                        </script></body>""",
                    )

                await context.route("**/*", fixture)
                source = await acquire(await context.new_page(), "https://jobs.example/42")
                assert '"title":"Engineer 42"' in source.html
                assert "<h1>Engineer 42</h1><p>Fully remote</p>" in source.html
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.usefixtures("virtual_settling_clock")
@pytest.mark.parametrize(
    ("filename", "title", "sections"),
    [
        ("semantic-posting.html", "Platform Developer", ["Responsibilities", "Work schedule"]),
        ("structured-posting.html", "Systems Tester", ["Qualifications", "Location"]),
    ],
)
def test_authored_pages_retain_job_identity_and_substantive_sections(
    filename: str, title: str, sections: list[str]
) -> None:
    from pathlib import Path

    html = (Path("tests/fixtures/retrieval") / filename).read_text()

    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def fixture(route: Route) -> None:
                    if route.request.url != "https://jobs.example/posting":
                        await route.abort()
                        pytest.fail(f"Unexpected browser request: {route.request.url}")
                    await route.fulfill(content_type="text/html", body=html)

                await context.route("**/*", fixture)
                source = await acquire(await context.new_page(), "https://jobs.example/posting")
                assert title in source.html
                for section in sections:
                    assert section in source.html
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.usefixtures("virtual_settling_clock")
@pytest.mark.parametrize("aborted", [False, True])
def test_incomplete_frame_fails_even_with_readable_main_job(aborted: bool) -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def fixture(route: Route) -> None:
                    if route.request.url == "https://jobs.example/42":
                        await route.fulfill(
                            content_type="text/html",
                            body='<h1>Engineer 42</h1><iframe src="https://ats.example/42"></iframe>',
                        )
                    elif aborted:
                        await route.abort()
                    else:
                        await route.fulfill(status=403, body="Blocked job description")

                await context.route("**/*", fixture)
                with pytest.raises(RetrievalError, match="frame"):
                    await acquire(await context.new_page(), "https://jobs.example/42")
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
def test_svg_text_and_accessible_labels_are_kept_as_evidence() -> None:
    from job_scan.retrieval import SNAPSHOT

    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(
                    '<h1>Engineer</h1><svg aria-label="Hybrid work">'
                    "<title>Home office</title><text>Two days weekly</text>"
                    '<path d="M0,0"/></svg><span aria-label="Remote option"></span>'
                )
                html = await page.evaluate(SNAPSHOT)
                assert "Hybrid work" in html
                assert "Home office" in html
                assert "Two days weekly" in html
                assert 'aria-label="Remote option"' in html
                assert "<path" not in html
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.usefixtures("virtual_settling_clock")
@pytest.mark.parametrize("empty_frame", [False, True])
def test_missing_description_does_not_turn_into_an_uncertain_assessment(empty_frame: bool) -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def fixture(route: Route) -> None:
                    if route.request.url == "https://jobs.example/42":
                        description = (
                            '<iframe src="https://ats.example/description"></iframe>'
                            if empty_frame
                            else "<script>fetch('/description').then(r=>r.text())</script>"
                        )
                        await route.fulfill(
                            content_type="text/html", body="<h1>Engineer 42</h1>" + description
                        )
                    else:
                        await route.fulfill(status=200 if empty_frame else 503, body="")

                await context.route("**/*", fixture)
                with pytest.raises(RetrievalError):
                    await acquire(await context.new_page(), "https://jobs.example/42")
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
def test_hidden_alternative_job_claims_retain_visibility_context() -> None:
    from job_scan.retrieval import SNAPSHOT

    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(
                    "<style>.inactive {display:none}</style><h1>Engineer 42</h1>"
                    '<p>On-site in Vienna</p><section class="inactive">'
                    "<h1>Other job</h1><p>Fully remote</p></section>"
                    '<p hidden>Old schedule</p><span aria-hidden="true">Old badge</span>'
                    '<svg hidden aria-hidden="true"><title>Old remote badge</title></svg>'
                )
                html = await page.evaluate(SNAPSHOT)
                assert "On-site in Vienna" in html
                assert 'data-rendered-hidden="true"' in html
                assert " hidden" in html
                assert 'aria-hidden="true"' in html
                assert "Fully remote" in html
                visibility = await page.evaluate(
                    """html => {
                    const root = document.createElement('div');
                    root.innerHTML = html;
                    const badge = [...root.querySelectorAll('span')]
                        .find(node => node.textContent === 'Old remote badge');
                    return badge.hasAttribute('hidden') &&
                        badge.getAttribute('data-rendered-hidden') === 'true' &&
                        badge.getAttribute('aria-hidden') === 'true';
                }""",
                    html,
                )
                assert visibility
            finally:
                await browser.close()

    asyncio.run(scenario())


@pytest.mark.enable_socket
@pytest.mark.usefixtures("virtual_settling_clock")
@pytest.mark.parametrize("aborted", [False, True])
def test_failed_identity_request_also_prevents_assessment(aborted: bool) -> None:
    async def scenario() -> None:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                context = await browser.new_context()

                async def fixture(route: Route) -> None:
                    if route.request.url == "https://jobs.example/42":
                        await route.fulfill(
                            content_type="text/html",
                            body=(
                                "<h1>Engineer 42</h1><p>Build and maintain backend services.</p>"
                                "<p>Fully remote</p><script>"
                                "fetch('https://identity.example/session').catch(() => {})</script>"
                            ),
                        )
                    elif not aborted:
                        await route.fulfill(status=401, body="Not signed in")
                    else:
                        await route.abort()

                await context.route("**/*", fixture)
                with pytest.raises(RetrievalError, match="content request failed"):
                    await acquire(await context.new_page(), "https://jobs.example/42")
            finally:
                await browser.close()

    asyncio.run(scenario())
