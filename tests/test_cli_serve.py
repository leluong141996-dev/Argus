from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest import mock  # noqa: E402
from core import cli  # noqa: E402


def test_serve_subcommand_builds_app_and_runs_uvicorn():
    with mock.patch("uvicorn.run") as run, \
         mock.patch("server.app.create_app") as create_app:
        rc = cli.main(["serve", "--host", "0.0.0.0", "--port", "9001"])
    assert rc == 0
    create_app.assert_called_once()
    run.assert_called_once()
    _, kwargs = run.call_args
    assert kwargs.get("host") == "0.0.0.0"
    assert kwargs.get("port") == 9001
