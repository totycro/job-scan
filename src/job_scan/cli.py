"""Imperative shell: file loading, credentials, HTTP, and terminal output."""

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import jwt

from job_scan.ai import DEFAULT_MODEL, ResponsesClient
from job_scan.auth import ChatGPTSession
from job_scan.evidence import assess
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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="job-scan", description="Assess saved job-posting HTML.")
    commands = root.add_subparsers(dest="command", required=True)
    assessment = commands.add_parser("assess", help="Assess one saved HTML file")
    assessment.add_argument("posting", type=Path)
    assessment.add_argument("--source-url")
    assessment.add_argument("--model", default=DEFAULT_MODEL)
    commands.add_parser("models", help="List models available to the signed-in account")
    auth = commands.add_parser("auth", help="ChatGPT sign-in and registrations")
    actions = auth.add_subparsers(dest="action", required=True)
    login = actions.add_parser("login")
    login.add_argument("--account")
    actions.add_parser("status")
    use = actions.add_parser("use")
    use.add_argument("registration")
    actions.add_parser("logout")
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        # Load and reject invalid inputs before opening auth/network resources.
        source = load_posting(args.posting, args.source_url) if args.command == "assess" else None
        with ChatGPTSession() as session:
            if args.command == "auth":
                if args.action == "login":
                    session.login(args.account)
                    session.access_token()  # Identity-only sign-in cannot enable inference.
                    print("ChatGPT plan access authorized.")
                elif args.action == "status":
                    print("\n".join(safe(s) for s in session.status()) or "No saved registrations.")
                elif args.action == "use":
                    session.select(args.registration)
                    print("Active registration selected.")
                else:
                    confirmed = session.sign_out()
                    print(
                        "Signed out locally. "
                        + (
                            "Remote revocation confirmed."
                            if confirmed
                            else "Remote revocation could not be confirmed."
                        )
                    )
            else:
                with ResponsesClient(session) as client:
                    if args.command == "models":
                        for model in client.models():
                            print(safe(f"{model.slug}\t{model.display_name}"))
                    elif source is not None:
                        result = client.assess_html(source.html, args.model)
                        print(
                            render(assess(source, result, client.returned_model or args.model)),
                            end="",
                        )
        return 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    except KeyboardInterrupt:
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
