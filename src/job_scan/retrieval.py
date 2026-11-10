"""Browser acquisition shell and deterministic evidence-document assembly."""

import asyncio
import hashlib
from dataclasses import dataclass
from html import escape
from urllib.parse import urlsplit

from playwright.async_api import Error as BrowserError
from playwright.async_api import Frame, Page, Request, Response, async_playwright

from job_scan.browser_network import public_proxy
from job_scan.models import PostingInput

MAX_BYTES = 262144
MAX_FRAMES = 24
DEADLINE_SECONDS = 60
FALLBACK = "Save the posting as HTML, then use: job-scan assess posting.html --source-url URL"

SNAPSHOT = """() => {
    if (!document.body) return '';
    const clone = node => {
        const result = node.cloneNode(false);
        if (node.nodeType === Node.ELEMENT_NODE) {
            const style = getComputedStyle(node);
            if (node.hasAttribute('hidden') || style.display === 'none' ||
                ['hidden', 'collapse'].includes(style.visibility))
                result.setAttribute('data-rendered-hidden', 'true');
        }
        for (const child of node.childNodes) result.appendChild(clone(child));
        if (node.shadowRoot) {
            for (const child of node.shadowRoot.childNodes) result.appendChild(clone(child));
        }
        return result;
    };
    const body = clone(document.body);
    for (const svg of body.querySelectorAll('svg')) {
        const text = document.createElement('span');
        for (const name of ['hidden', 'aria-hidden', 'data-rendered-hidden']) {
            if (svg.hasAttribute(name)) text.setAttribute(name, svg.getAttribute(name));
        }
        text.textContent = [svg.getAttribute('aria-label') || '',
            ...[...svg.querySelectorAll('title,desc,text')].map(node => node.textContent)]
            .filter(Boolean).join(' ');
        svg.replaceWith(text);
    }
    body.querySelectorAll('script:not([type="application/ld+json"]),style,link')
        .forEach(node => node.remove());
    for (const node of body.querySelectorAll('*')) {
        for (const attr of [...node.attributes]) {
            const keep = ['href', 'alt', 'title', 'colspan', 'rowspan', 'type', 'aria-label',
                'hidden', 'aria-hidden', 'aria-selected', 'aria-expanded', 'data-rendered-hidden'];
            if (node.tagName === 'IFRAME') keep.push('src');
            if (!keep.includes(attr.name))
                node.removeAttribute(attr.name);
        }
    }
    const structured = [...document.head.querySelectorAll('script[type="application/ld+json"]')]
        .map(node => node.outerHTML).join('\\n');
    return structured + '\\n' + body.innerHTML;
}"""


class RetrievalError(RuntimeError):
    """No sufficiently complete posting was acquired."""


def validate_url(url: str) -> str:
    """Validate without normalizing away job-selecting parameters or fragments."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
        if (
            parsed.scheme not in {"http", "https"}
            or not bool(parsed.hostname)
            or parsed.username is not None
            or parsed.password is not None
            or any(c.isspace() or not c.isprintable() for c in url)
            or port == 0
        ):
            raise ValueError
    except ValueError:
        raise ValueError(
            "Posting URL must be an HTTP(S) URL without credentials or whitespace."
        ) from None
    return url


@dataclass(frozen=True)
class Document:
    url: str
    html: str
    readable: bool = True


def assemble_documents(submitted_url: str, documents: list[Document]) -> PostingInput:
    """Preserve complete content and identify every contributing source."""
    if not documents or not any(d.html.strip() for d in documents):
        raise RetrievalError("The page has no readable posting content.")
    if any(not d.readable and urlsplit(d.url).scheme in {"http", "https"} for d in documents[1:]):
        raise RetrievalError("A visible posting frame has no readable content.")
    if len(documents) > MAX_FRAMES:
        raise RetrievalError("The page exceeds the 24-document retrieval limit.")
    parts = [
        '<article aria-label="Retrieved posting">',
        f"<p>Submitted posting URL: {escape(submitted_url)}</p>",
    ]
    for document in documents:
        parts += [
            f'<section data-source-url="{escape(document.url, quote=True)}">',
            f"<p>Document URL: {escape(document.url)}</p>",
            document.html,
            "</section>",
        ]
    parts.append("</article>")
    html = "\n".join(parts)
    content = html.encode()
    if len(content) > MAX_BYTES:
        raise RetrievalError("Retrieved posting exceeds the 256 KiB limit; nothing was truncated.")
    return PostingInput(
        path=None,
        source_url=submitted_url,
        final_url=documents[0].url,
        frame_urls=list(dict.fromkeys(d.url for d in documents[1:])),
        html=html,
        sha256=hashlib.sha256(content).hexdigest(),
    )


async def read_documents(page: Page) -> tuple[list[Document], set[Frame]]:
    """Read visible frames through Playwright, including cross-origin documents."""
    frames = page.frames
    if len(frames) > MAX_FRAMES:
        raise RetrievalError("The page exceeds the 24-document retrieval limit.")
    documents = []
    contributing = set()
    for frame in frames:
        if frame != page.main_frame and not await (await frame.frame_element()).is_visible():
            continue
        await frame.wait_for_load_state("domcontentloaded")
        readable = await frame.evaluate("""() => Boolean(document.body?.innerText.trim() ||
            document.querySelector('script[type="application/ld+json"]')?.textContent.trim())""")
        if (
            frame != page.main_frame
            and not readable
            and frame.url in {"about:blank", "about:srcdoc"}
        ):
            continue
        documents.append(Document(frame.url, await frame.evaluate(SNAPSHOT), readable))
        contributing.add(frame)
    return documents, contributing


def posting_data_request(request: Request) -> bool:
    return request.resource_type in {"xhr", "fetch"}


async def acquire(page: Page, url: str) -> PostingInput:
    """Render until content settles; caller bounds the entire browser lifecycle."""
    failures: dict[Frame, int] = {}
    content_requests: dict[tuple[Frame, str], int] = {}

    def response_status(response: Response) -> None:
        if response.request.resource_type == "document":
            failures[response.frame] = response.status
        elif posting_data_request(response.request):
            content_requests[response.frame, response.url] = response.status

    def request_failed(request: Request) -> None:
        if request.is_navigation_request():
            failures[request.frame] = 599
        elif posting_data_request(request):
            content_requests[request.frame, request.url] = 599

    page.on("response", response_status)
    page.on("requestfailed", request_failed)
    response = await page.goto(url, wait_until="domcontentloaded")
    if response is None or response.status >= 400:
        raise RetrievalError("The posting was blocked or unavailable (HTTP response failed).")
    loop = asyncio.get_running_loop()
    started = loop.time()
    unchanged_since = started
    previous: list[Document] = []
    while True:
        documents, contributing = await read_documents(page)
        if documents != previous:
            previous = documents
            unchanged_since = loop.time()
        if loop.time() - started >= 5 and loop.time() - unchanged_since >= 2:
            break
        await asyncio.sleep(0.5)
    if any(failures.get(frame, 200) >= 400 for frame in contributing):
        raise RetrievalError("A posting frame was blocked or unavailable.")
    if any(
        status >= 400 for (frame, _url), status in content_requests.items() if frame in contributing
    ):
        raise RetrievalError(
            "A page content request failed; posting completeness cannot be verified."
        )
    return assemble_documents(url, documents)


async def _retrieve(url: str) -> PostingInput:
    async with (
        asyncio.timeout(DEADLINE_SECONDS),
        public_proxy() as proxy,
        async_playwright() as playwright,
    ):
        browser = await playwright.chromium.launch(
            proxy={"server": proxy, "bypass": "<-loopback>"},
            args=["--force-webrtc-ip-handling-policy=disable_non_proxied_udp"],
        )
        try:
            context = await browser.new_context(service_workers="block")
            page = await context.new_page()
            return await acquire(page, url)
        finally:
            await browser.close()


def retrieve_posting(url: str) -> PostingInput:
    """Acquire once before authentication; never prompt or reuse browser credentials."""
    validate_url(url)
    try:
        return asyncio.run(_retrieve(url))
    except TimeoutError:
        raise RetrievalError(f"Posting retrieval exceeded 60 seconds. {FALLBACK}") from None
    except BrowserError, OSError:
        raise RetrievalError(
            "Browser retrieval failed. Check connectivity and install Chromium with "
            f"`uv run --locked playwright install chromium`. {FALLBACK}"
        ) from None
    except RetrievalError as exc:
        raise RetrievalError(f"{exc} {FALLBACK}") from None
