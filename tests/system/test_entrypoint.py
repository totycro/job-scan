import shutil
import subprocess


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
