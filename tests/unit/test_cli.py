from pathlib import Path

import pytest

from job_scan.cli import load_posting, main


def test_input_bytes_and_limits(tmp_path: Path) -> None:
    path = tmp_path / "posting.html"
    path.write_bytes(b"\xef\xbb\xbf<html>\r\nremote</html>")
    source = load_posting(path, "https://example.com/job")
    assert source.html == "<html>\r\nremote</html>"
    assert len(source.sha256) == 64
    path.write_bytes(b"x" * 262144)
    assert len(load_posting(path).html) == 262144
    for content in (b"", b" \n", b"\xff", b"x" * 262145):
        path.write_bytes(content)
        with pytest.raises(ValueError):
            load_posting(path)
    for bad_path in (tmp_path, tmp_path / "absent"):
        with pytest.raises(ValueError):
            load_posting(bad_path)
    for url in ("ftp://example.com", "https:///job", "garbage"):
        with pytest.raises(ValueError):
            load_posting(path, url)


def test_cli_args_and_no_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert main(["--help"]) == 0
    assert main([]) == 2
    assert main(["assess", str(tmp_path / "missing")]) == 2
    path = tmp_path / "job.html"
    path.write_text("<h1>Engineer</h1>Fully remote")
    assert main(["assess", str(path)]) == 1
    captured = capsys.readouterr()
    assert "Sign in" in captured.err
    assert main(["auth", "status"]) == 0
    assert main(["auth", "logout"]) == 0
    assert main(["auth", "use", "missing"]) == 1


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["unknown"],
        ["auth"],
        ["auth", "use"],
        ["assess"],
        ["assess", "one.html", "two.html"],
        ["assess", "one.html", "--model"],
        ["assess", "one.html", "--source-url"],
        ["assess", "one.html", "--unknown"],
        ["auth", "login", "--account"],
    ],
)
def test_invalid_arguments_do_not_open_session(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unexpected_session() -> None:
        pytest.fail("Invalid arguments must fail before opening an authentication session")

    monkeypatch.setattr("job_scan.cli.ChatGPTSession", unexpected_session)
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--help"], ["assess", "models", "auth"]),
        (["assess", "--help"], ["POSTING", "--source-url", "--model"]),
        (["auth", "--help"], ["login", "status", "use", "logout"]),
        (["auth", "login", "--help"], ["--account"]),
        (["auth", "use", "--help"], ["REGISTRATION"]),
    ],
)
def test_help_without_authentication(
    argv: list[str],
    expected: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_session() -> None:
        pytest.fail("Help must not open an authentication session")

    monkeypatch.setattr("job_scan.cli.ChatGPTSession", unexpected_session)
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert all(text.casefold() in captured.out.casefold() for text in expected)
    assert "\x1b" not in captured.out


def test_interrupted_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupted_status(_session: object) -> list[str]:
        raise KeyboardInterrupt

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("job_scan.cli.ChatGPTSession.status", interrupted_status)
    assert main(["auth", "status"]) == 130
    captured = capsys.readouterr()
    assert not captured.out
    assert "Interrupted." in captured.err


def test_profile_file_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib

    from job_scan.cli import InputError, load_profile

    path = tmp_path / "preferences.toml"
    example = Path("specs/002-personalized-job-ratings/contracts/profile.example.toml").read_bytes()
    for content in [
        example,
        b"\xef\xbb\xbf" + example,
        example + b"\n#" + b" " * (65536 - len(example) - 2),
    ]:
        path.write_bytes(content)
        loaded = load_profile(path)
        assert loaded.sha256 == hashlib.sha256(content).hexdigest()
        assert loaded.path == path
        assert path.read_bytes() == content
    for content in [b"", b"\xff", b" " * 65537, b"schema_version = 1\nschema_version = 1"]:
        path.write_bytes(content)
        with pytest.raises(InputError):
            load_profile(path)
    for invalid in [tmp_path / "missing", tmp_path]:
        with pytest.raises(InputError):
            load_profile(invalid)
    path.write_bytes(example)
    real_open = Path.open
    calls = []

    def counting_open(self: Path, mode: str = "r") -> object:
        if self == path:
            calls.append(self)
        return real_open(self, mode)

    monkeypatch.setattr(Path, "open", counting_open)
    load_profile(path)
    assert calls == [path]


@pytest.mark.parametrize(
    "content",
    [b"", b"\xff", b" " * 65537, b'schema_version = "PRIVATE-PROFILE"', b"PRIVATE-PROFILE = ["],
)
def test_invalid_profile_before_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    content: bytes,
) -> None:
    from job_scan.cli import main

    posting = tmp_path / "posting.html"
    posting.write_text("backend development")
    profile = tmp_path / "preferences.toml"
    profile.write_bytes(content)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Invalid local input constructed an auth or network client")

    monkeypatch.setattr("job_scan.cli.ChatGPTSession", forbidden)
    monkeypatch.setattr("job_scan.cli.ResponsesClient", forbidden)
    assert main(["assess", str(posting), "--profile", str(profile)]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "Profile" in captured.err
    assert "PRIVATE-PROFILE" not in captured.err


def test_profile_read_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from job_scan.cli import InputError, load_profile

    path = tmp_path / "profile.toml"
    path.touch()

    def unreadable(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("PRIVATE-PROFILE")

    monkeypatch.setattr(Path, "open", unreadable)
    with pytest.raises(InputError, match="unable to read") as failure:
        load_profile(path)
    assert "PRIVATE-PROFILE" not in str(failure.value)


@pytest.mark.parametrize(
    "argv",
    [
        ["assess", "https://example.com/job", "--source-url", "https://other.example/job"],
        ["assess", "ftp://example.com/job"],
        ["assess", "https://user:secret@example.com/job"],
    ],
)
def test_invalid_url_arguments_before_acquisition(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Invalid input started acquisition or authentication")

    monkeypatch.setattr("job_scan.cli.retrieve_posting", forbidden)
    monkeypatch.setattr("job_scan.cli.ChatGPTSession", forbidden)
    assert main(argv) == 2
    assert not capsys.readouterr().out
