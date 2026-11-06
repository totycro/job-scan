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
