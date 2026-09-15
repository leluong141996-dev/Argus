"""Shared constants and helpers for the `agentic_coding` task.

No scoring logic lives here -- just the machine-readable failure tags the
scorer, the baselines, and the tests all reference by name, plus the helper
that names a case's canonical test paths.
"""

from __future__ import annotations

from typing import Any

# Failure/behaviour tags (single source of truth).
INVALID_JSON = "invalid_json"            # output not parseable to an object
MALFORMED_PATCH = "malformed_patch"      # `files` present but wrong shape
FORBIDDEN_PATH = "forbidden_path"        # wrote outside allowed_paths
VISIBLE_TESTS_FAILED = "visible_tests_failed"
HIDDEN_TESTS_FAILED = "hidden_tests_failed"
TEST_TAMPERING = "test_tampering"        # wrote to a visible/hidden test path
SANDBOX_ERROR = "sandbox_error"          # timeout / crash / no collection


def test_paths(case: dict[str, Any]) -> set[str]:
    """The canonical test paths for a case (visible + hidden). Writing to any
    of these is tampering, regardless of allowed_paths."""
    return set(case.get("visible_tests", {})) | set(case.get("hidden_tests", {}))
