"""Imperative shell: file loading, credentials, HTTP, and terminal output."""

import hashlib
import sys
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import httpx
import jwt
import typer

from job_scan.ai import DEFAULT_MODEL, ResponsesClient
from job_scan.auth import ChatGPTSession
from job_scan.evidence import assess as assess_posting
from job_scan.models import PostingInput
from job_scan.report import render, safe

MAX_BYTES = 262144


class InputError(ValueError):
    """Invalid local input; exit 2 before any inference."""


def load_posting(path: Path, source_url: str | None = None) -> PostingInput:
    if source_url is not None:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not bool(parsed.hostname):
            raise InputError("Source URL must be an HTTP(S) URL; it is never fetched.")
    try:
        if not path.is_file():
            raise InputError("Input must be a readable regular HTML file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise InputError("Input exceeds the 256 KiB limit; no content was truncated or sent.")
        html = content.decode("utf-8-sig")
    except OSError, UnicodeError:
        raise InputError("Unable to read input as UTF-8 HTML.") from None
    if not html.strip():
        raise InputError("Input HTML is empty.")
    return PostingInput(
        path=path, source_url=source_url, html=html, sha256=hashlib.sha256(content).hexdigest()
    )


app = typer.Typer(
    help="Assess saved job-posting HTML.",
    add_completion=False,
    no_args_is_help=False,
    pretty_exceptions_enable=False,
)
auth_app = typer.Typer(help="ChatGPT sign-in and registrations", no_args_is_help=False)
app.add_typer(auth_app, name="auth")


@app.command()
def assess(
    posting: Annotated[Path, typer.Argument(help="Saved UTF-8 posting HTML (up to 256 KiB).")],
    source_url: Annotated[
        str | None, typer.Option(help="HTTP(S) source URL for provenance; never fetched.")
    ] = None,
    model: Annotated[str, typer.Option(help="Account-available model to use.")] = DEFAULT_MODEL,
) -> None:
    """Assess one saved HTML file."""
    source = load_posting(posting, source_url)
    with ChatGPTSession() as session, ResponsesClient(session) as client:
        result = client.assess_html(source.html, model)
        print(render(assess_posting(source, result, client.returned_model or model)), end="")


@app.command()
def models() -> None:
    """List models available to the signed-in account."""
    with ChatGPTSession() as session, ResponsesClient(session) as client:
        for model in client.models():
            print(safe(f"{model.slug}\t{model.display_name}"))


@auth_app.command()
def login(
    account: Annotated[str | None, typer.Option(help="Reuse an existing registration ID.")] = None,
) -> None:
    """Sign in and authorize ChatGPT plan access."""
    with ChatGPTSession() as session:
        session.login(account)
        session.access_token()  # Identity-only sign-in cannot enable inference.
        print("ChatGPT plan access authorized.")


@auth_app.command()
def status() -> None:
    """Show saved registrations without refreshing credentials."""
    with ChatGPTSession() as session:
        print("\n".join(safe(s) for s in session.status()) or "No saved registrations.")


@auth_app.command()
def use(registration: Annotated[str, typer.Argument(help="Saved registration ID.")]) -> None:
    """Select the active registration."""
    with ChatGPTSession() as session:
        session.select(registration)
        print("Active registration selected.")


@auth_app.command()
def logout() -> None:
    """Clear active credentials and attempt remote revocation."""
    with ChatGPTSession() as session:
        confirmed = session.sign_out()
        print(
            "Signed out locally. "
            + (
                "Remote revocation confirmed."
                if confirmed
                else "Remote revocation could not be confirmed."
            )
        )


def main(argv: list[str] | None = None) -> int:
    try:
        result = app(args=argv, prog_name="job-scan", standalone_mode=False)
        if result == 130:
            print("Interrupted.", file=sys.stderr)
        return result if isinstance(result, int) else 0
    except typer.TyperException as exc:
        print(safe(exc.format_message()), file=sys.stderr)
        return exc.exit_code
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    except KeyboardInterrupt, typer.Abort:
        print("Interrupted.", file=sys.stderr)
        return 130
    except InputError as exc:
        print(safe(str(exc)), file=sys.stderr)
        return 2
    except httpx.HTTPError, jwt.PyJWTError, OSError:
        print(
            "Authentication or network operation failed. Check sign-in and connectivity.",
            file=sys.stderr,
        )
        return 1
    except ValueError:
        print(
            "Assessment or authentication data is invalid; no report was produced.", file=sys.stderr
        )
        return 1
    except RuntimeError as exc:
        print(safe(str(exc)), file=sys.stderr)
        return 1


def entrypoint() -> None:
    raise SystemExit(main())
