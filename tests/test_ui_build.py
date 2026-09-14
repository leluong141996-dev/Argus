from __future__ import annotations
import shutil, subprocess
from pathlib import Path
import pytest

UI = Path(__file__).resolve().parents[1] / "ui"


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not available")
def test_ui_builds():
    if not (UI / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=UI, check=True)
    subprocess.run(["npm", "run", "build"], cwd=UI, check=True)
    assert (UI / "dist" / "index.html").exists()
