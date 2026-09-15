"""Execution sandbox for the agentic_coding task plugin.

A small, deterministic runner -- NOT a general framework. `LocalSandbox`
copies a pinned fixture into a temp dir, overlays the candidate's files,
writes the CANONICAL visible + hidden tests last (so a candidate cannot
neuter the tests actually run), and runs pytest in a bounded, offline
subprocess. Given a fixed (fixture, candidate, tests, timeout) the verdict
is deterministic, so the baseline gate can use it directly and keep its
teeth.

Security posture: `LocalSandbox` executes model-produced code. It is bounded
by a fresh temp dir, a hard wall-clock timeout, a scrubbed environment (no
inherited secrets), no granted network, and rejection of candidate paths that
escape the temp dir. OS-level isolation (containers/nsjail/seccomp) is out of
scope; a real run against untrusted model output belongs in a disposable
environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class TestResult:
    __test__ = False  # suppress PytestCollectionWarning (name starts with "Test")
    name: str
    passed: bool


@dataclass
class SandboxResult:
    applied: bool
    timed_out: bool
    error: str | None
    visible: list[TestResult]
    hidden: list[TestResult]

    @property
    def visible_passed(self) -> bool:
        return bool(self.visible) and all(t.passed for t in self.visible)

    @property
    def hidden_passed(self) -> bool:
        return bool(self.hidden) and all(t.passed for t in self.hidden)


class Sandbox(ABC):
    @abstractmethod
    def run(self, *, repo_files: dict[str, str], candidate_files: dict[str, str],
            visible_tests: dict[str, str], hidden_tests: dict[str, str],
            timeout_s: float) -> SandboxResult:
        raise NotImplementedError


def _safe_join(root: Path, rel: str) -> Path | None:
    """Resolve `rel` under `root`; return None if it escapes `root`."""
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved == target or root_resolved in target.parents:
        return target
    return None


def _write_files(root: Path, files: dict[str, str]) -> str | None:
    """Write each path->contents under root. Return an error string if any
    path escapes root; otherwise None."""
    for rel, contents in files.items():
        target = _safe_join(root, rel)
        if target is None:
            return f"unsafe path escapes sandbox root: {rel!r}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    return None


class LocalSandbox(Sandbox):
    def run(self, *, repo_files: dict[str, str], candidate_files: dict[str, str],
            visible_tests: dict[str, str], hidden_tests: dict[str, str],
            timeout_s: float) -> SandboxResult:
        with tempfile.TemporaryDirectory(prefix="argus-sbx-") as tmp:
            root = Path(tmp)
            # 1) fixture, 2) candidate overlay, 3) CANONICAL tests LAST.
            for group in (repo_files, candidate_files):
                err = _write_files(root, group)
                if err is not None:
                    applied = group is candidate_files  # True only when repo wrote OK, candidate failed
                    return SandboxResult(applied=applied, timed_out=False, error=err,
                                         visible=[], hidden=[])
            for group in (visible_tests, hidden_tests):
                err = _write_files(root, group)
                if err is not None:
                    return SandboxResult(applied=True, timed_out=False, error=err,
                                         visible=[], hidden=[])

            visible, verr, vtimed = self._run_pytest(root, list(visible_tests), timeout_s, root)
            hidden, herr, htimed = self._run_pytest(root, list(hidden_tests), timeout_s, root)
            error = verr or herr
            return SandboxResult(applied=True, timed_out=vtimed or htimed, error=error,
                                 visible=visible, hidden=hidden)

    @staticmethod
    def _scrubbed_env(root: Path) -> dict[str, str]:
        # Minimal environment: no inherited API keys/secrets, no network hints.
        keep = {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT"}
        env = {k: v for k, v in os.environ.items() if k in keep}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["HOME"] = str(root)  # avoid confusing errors from Path.home()/expanduser("~")
        return env

    def _run_pytest(self, root: Path, test_files: list[str],
                    timeout_s: float, sandbox_root: Path) -> tuple[list[TestResult], str | None, bool]:
        """Run pytest over `test_files` (relative to root). Returns
        (results, error, timed_out). No test files -> empty results, no error."""
        if not test_files:
            return [], None, False
        report = root / "_argus_report.xml"
        report.unlink(missing_ok=True)  # prevent stale report from previous run bleeding through
        cmd = [sys.executable, "-m", "pytest", *test_files,
               "--junitxml", str(report), "-p", "no:cacheprovider", "-q"]
        try:
            proc = subprocess.run(cmd, cwd=str(root), env=self._scrubbed_env(sandbox_root),
                                  capture_output=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return [], "timeout", True
        except Exception as exc:  # noqa: BLE001 - fail safe on any exec failure
            return [], f"sandbox exec error: {exc}", False

        if not report.exists():
            # No report => collection crashed (e.g. syntax error in candidate).
            tail = proc.stderr.decode("utf-8", "replace")[-500:]
            return [], f"pytest produced no report (rc={proc.returncode}): {tail}", False
        try:
            results = self._parse_junit(report)
        except ET.ParseError as exc:
            return [], f"unparseable report: {exc}", False
        if not results and proc.returncode not in (0, 1):
            return [], f"no tests collected (rc={proc.returncode})", False
        return results, None, False

    @staticmethod
    def _parse_junit(report: Path) -> list[TestResult]:
        tree = ET.parse(str(report))
        out: list[TestResult] = []
        for case in tree.iter("testcase"):
            failed = any(case.find(tag) is not None
                         for tag in ("failure", "error", "skipped"))
            name = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
            out.append(TestResult(name=name or case.get("name", "?"), passed=not failed))
        return out


class StubSandbox(Sandbox):
    """Returns a fixed SandboxResult; ignores its arguments. Unit tests only."""

    def __init__(self, result: SandboxResult) -> None:
        self._result = result

    def run(self, *, repo_files: dict[str, str], candidate_files: dict[str, str],
            visible_tests: dict[str, str], hidden_tests: dict[str, str],
            timeout_s: float) -> SandboxResult:
        return self._result
