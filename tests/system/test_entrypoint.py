import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("argv", [["--help"], ["assess", "--help"], ["auth", "status"]])
def test_lightweight_commands_defer_assessment_imports(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    script = """
import sys
from job_scan.cli import main

result = main(sys.argv[1:])
assert result == 0, result
assessment_modules = {
    "job_scan.ai", "job_scan.evidence", "job_scan.models", "job_scan.profiles",
    "job_scan.rating_models", "job_scan.ratings",
}
assert not (loaded := assessment_modules.intersection(sys.modules)), loaded
"""
    result = subprocess.run(  # noqa: S603 - fixed local script and test-owned arguments.
        [sys.executable, "-c", script, *argv], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_installed_help() -> None:
    executable = shutil.which("job-scan")
    assert executable is not None
    result = subprocess.run([executable, "--help"], capture_output=True, text=True, check=False)  # noqa: S603 - installed local entry point with fixed arguments.
    assert result.returncode == 0
    assert "assess" in result.stdout


def test_installed_assess_help() -> None:
    executable = shutil.which("job-scan")
    assert executable is not None
    result = subprocess.run(  # noqa: S603 - installed local entry point with fixed arguments.
        [executable, "assess", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "--profile" in result.stdout
    assert "--source-url" in result.stdout
    assert "--model" in result.stdout
