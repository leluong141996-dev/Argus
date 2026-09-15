from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.sandbox import LocalSandbox, SandboxResult, StubSandbox, TestResult  # noqa: E402

ADD_REPO = {"adder.py": "def add(a, b):\n    return a + b\n"}
VISIBLE = {"test_visible.py": "from adder import add\n\ndef test_adds():\n    assert add(1, 2) == 3\n"}
HIDDEN = {"test_hidden.py": "from adder import add\n\ndef test_zero():\n    assert add(0, 0) == 0\n"}


def test_correct_candidate_passes_both():
    sb = LocalSandbox()
    res = sb.run(repo_files=ADD_REPO, candidate_files={}, visible_tests=VISIBLE,
                 hidden_tests=HIDDEN, timeout_s=30)
    assert res.applied and res.error is None and not res.timed_out
    assert res.visible_passed and res.hidden_passed
    assert {t.passed for t in res.visible} == {True}


def test_broken_candidate_fails_tests():
    sb = LocalSandbox()
    res = sb.run(repo_files=ADD_REPO,
                 candidate_files={"adder.py": "def add(a, b):\n    return a - b\n"},
                 visible_tests=VISIBLE, hidden_tests=HIDDEN, timeout_s=30)
    # add(1,2) -> -1 != 3 (visible fails); add(0,0) -> 0 (hidden passes)
    assert res.error is None
    assert not res.visible_passed
    assert res.hidden_passed


def test_canonical_tests_are_authoritative():
    # A candidate that writes a passing stub over the hidden-test path cannot
    # neuter it: the sandbox writes the canonical tests LAST.
    sb = LocalSandbox()
    res = sb.run(repo_files=ADD_REPO,
                 candidate_files={"test_hidden.py": "def test_zero():\n    assert True\n",
                                  "adder.py": "def add(a, b):\n    return 999\n"},
                 visible_tests=VISIBLE, hidden_tests=HIDDEN, timeout_s=30)
    # canonical hidden test (add(0,0)==0) runs against add->999 and FAILS
    assert not res.hidden_passed


def test_timeout_is_fail_safe():
    sb = LocalSandbox()
    res = sb.run(repo_files={"adder.py": "while True:\n    pass\n"},
                 candidate_files={}, visible_tests=VISIBLE, hidden_tests={},
                 timeout_s=2)
    assert res.timed_out and res.error is not None
    assert not res.visible_passed and not res.hidden_passed


def test_path_escape_is_rejected():
    sb = LocalSandbox()
    res = sb.run(repo_files=ADD_REPO, candidate_files={"../evil.py": "x = 1\n"},
                 visible_tests=VISIBLE, hidden_tests=HIDDEN, timeout_s=30)
    # H1: repo_files wrote successfully → applied=True; candidate was the bad actor
    assert res.applied and res.error is not None
    assert not res.visible_passed


def test_stub_returns_canned_result():
    canned = SandboxResult(applied=True, timed_out=False, error=None,
                           visible=[TestResult("v", True)], hidden=[TestResult("h", False)])
    sb = StubSandbox(canned)
    res = sb.run(repo_files={}, candidate_files={}, visible_tests={}, hidden_tests={},
                 timeout_s=1)
    assert res is canned
    assert res.visible_passed and not res.hidden_passed


def test_stale_report_not_inherited_by_hidden_run():
    # Regression for B1: a hidden pytest run that crashes before writing XML must NOT
    # inherit the stale visible-run report. We force no XML by using os._exit in the
    # hidden test file — the subprocess terminates immediately, no report is written.
    # Without the `unlink` fix the visible XML would still exist and hidden_passed
    # would silently return True; with the fix hidden_passed must be False and error set.
    sb = LocalSandbox()
    res = sb.run(
        repo_files=ADD_REPO,
        candidate_files={},
        visible_tests=VISIBLE,
        hidden_tests={"test_crash_hidden.py": "import os; os._exit(99)\n"},
        timeout_s=30,
    )
    assert res.visible_passed
    assert not res.hidden_passed
    assert res.error is not None
