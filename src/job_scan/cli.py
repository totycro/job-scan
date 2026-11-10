"""Imperative shell: file loading, credentials, HTTP, and terminal output."""

import hashlib
import sys
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
lazy import httpx
lazy import jwt

from job_scan import DEFAULT_MODEL
lazy from job_scan.ai import ResponsesClient
lazy from job_scan.auth import ChatGPTSession
lazy from job_scan.evidence import AssessmentError
lazy from job_scan.evidence import assess as assess_posting
lazy from job_scan.models import PostingInput
lazy from job_scan.profiles import ProfileError, ProfileInput, has_exceptions, parse_profile
lazy from job_scan.rating_models import PassMetadata
lazy from job_scan.ratings import assemble, build_dimensions
lazy from job_scan.report import render, render_personalized, safe
lazy from job_scan.retrieval import FALLBACK, RetrievalError, retrieve_posting, validate_url

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


def load_profile(path: Path) -> ProfileInput:
    try:
        if not path.is_file():
            raise ProfileError("Profile must be a readable regular TOML file.")
        with path.open("rb") as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            raise ProfileError("Profile exceeds the 64 KiB limit; no content was sent.")
        if not content:
            raise ProfileError("Profile is empty.")
        profile = parse_profile(content.decode("utf-8-sig"))
    except OSError, UnicodeError:
        raise InputError(f"Profile {path}: unable to read UTF-8 TOML.") from None
    except ProfileError as exc:
        raise InputError(f"Profile {path}: {exc}") from None
    return ProfileInput(path=path, sha256=hashlib.sha256(content).hexdigest(), profile=profile)


app = typer.Typer(
    help="Assess job-posting URLs or saved HTML.",
    add_completion=False,
    no_args_is_help=False,
    pretty_exceptions_enable=False,
)
auth_app = typer.Typer(help="ChatGPT sign-in and registrations", no_args_is_help=False)
app.add_typer(auth_app, name="auth")


@app.command()
def assess(
    posting: Annotated[str, typer.Argument(help="Public HTTP(S) posting URL or saved UTF-8 HTML.")],
    source_url: Annotated[
        str | None, typer.Option(help="HTTP(S) source URL for provenance; never fetched.")
    ] = None,
    model: Annotated[str, typer.Option(help="Account-available model to use.")] = DEFAULT_MODEL,
    profile: Annotated[
        Path | None, typer.Option(help="UTF-8 preference TOML (up to 64 KiB). ")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show assessment progress on stderr.")
    ] = False,
) -> None:
    """Assess one posting from its URL or saved HTML."""
    is_url = "://" in posting
    if is_url:
        if source_url is not None:
            raise InputError(
                "--source-url is only for saved HTML; the posting URL supplies provenance."
            )
        try:
            validate_url(posting)
        except ValueError as exc:
            raise InputError(str(exc)) from None
    if profile is not None:
        progress("Loading preferences...", verbose)
    preferences = load_profile(profile) if profile is not None else None
    progress("Retrieving posting in browser..." if is_url else "Loading saved posting...", verbose)
    source = retrieve_posting(posting) if is_url else load_posting(Path(posting), source_url)
    try:
        assess_source(source, model, preferences, verbose)
    except AssessmentError as exc:
        if is_url:
            raise RetrievalError(f"{exc} {FALLBACK}") from None
        raise
    progress("Assessment complete.", verbose)


def progress(message: str, verbose: bool) -> None:
    """Emit fixed stage messages immediately, without source or credential data."""
    if verbose:
        print(message, file=sys.stderr, flush=True)


def assess_source(
    source: PostingInput, model: str, preferences: ProfileInput | None, verbose: bool = False
) -> None:
    """Use the same immutable evidence document for every inference pass."""
    progress("Opening authentication session...", verbose)
    with ChatGPTSession() as session, ResponsesClient(session) as client:
        progress("Assessing work arrangement...", verbose)
        result = (
            client.assess_html(source.html, model, target_url=source.source_url)
            if source.final_url is not None
            else client.assess_html(source.html, model)
        )
        work = assess_posting(source, result, client.returned_model or model)
        if preferences is None:
            print(render(work), end="")
            return
        passes = [
            PassMetadata(
                stage="work_arrangement",
                requested_model=model,
                returned_model=client.returned_model,
            )
        ]
        progress("Assessing preference fit...", verbose)
        fits = client.assess_fit(source.html, preferences.profile, model)
        passes.append(
            PassMetadata(stage="fit", requested_model=model, returned_model=client.returned_model)
        )
        build_dimensions(work, preferences, fits)
        exceptions = None
        if has_exceptions(preferences.profile):
            progress("Checking exceptional preferences...", verbose)
            exceptions = client.assess_exceptions(source.html, preferences.profile, model)
            passes.append(
                PassMetadata(
                    stage="exceptions", requested_model=model, returned_model=client.returned_model
                )
            )
        report = assemble(work, preferences, fits, passes, exceptions)
        print(render_personalized(report), end="")


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
