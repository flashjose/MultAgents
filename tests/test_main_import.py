import subprocess
import sys
from pathlib import Path


def test_main_can_run_as_script_from_repo_root():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "app" / "main.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr or result.stdout
