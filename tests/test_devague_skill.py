"""Smoke tests for the first-party ``devague`` skill wrapper.

These drive ``.claude/skills/devague/scripts/devague.sh`` via subprocess in a
sandboxed ``tmp_path`` cwd (so ``.devague/`` never touches the repo). They pin
the contract steward relies on when it pulls this skill into the mesh: the
wrapper forwards moves verbatim, ``status`` reads the convergence gate and names
the next move, and ``export`` stays blocked until the frame converges.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "devague" / "scripts" / "devague.sh"


def run(*args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _drive(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    proc = run(*args, cwd=cwd)
    assert proc.returncode == 0, f"{args} failed: {proc.stderr}"
    return proc


def test_script_is_executable_and_valid_bash() -> None:
    assert SCRIPT.exists(), f"missing wrapper at {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), "wrapper should be executable"
    # `bash -n` parses without running.
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_help_lists_moves(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "help")
    assert "operate the devague" in proc.stdout
    for move in ("new", "capture", "interrogate", "converge", "export", "status"):
        assert move in proc.stdout


def test_forwards_learn_verbatim(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "learn")
    assert "What's the announcement?" in proc.stdout


def test_status_reports_no_frames(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "status")
    assert "no frames yet" in proc.stdout


def test_status_names_gaps_and_next_move(tmp_path: Path) -> None:
    _drive(tmp_path, "new", "Devague ships a documented spec contract")
    proc = _drive(tmp_path, "status")
    assert "NOT passed" in proc.stdout
    assert "missing confirmed 'audience' claim" in proc.stdout
    # first gap -> capture the audience claim
    assert "devague capture --kind audience" in proc.stdout


def test_status_suggestion_does_not_imply_agent_confirm(tmp_path: Path) -> None:
    # A user-origin capture auto-confirms; the suggestion must not imply the
    # agent should run a follow-up `confirm` (the user-only-confirm hard rule).
    _drive(tmp_path, "new", "Devague ships a documented spec contract")
    proc = _drive(tmp_path, "status")
    assert "auto-confirm" in proc.stdout
    assert "then: devague confirm" not in proc.stdout


def test_status_header_reflects_frame_flag(tmp_path: Path) -> None:
    _drive(tmp_path, "new", "First frame")
    second = _drive(tmp_path, "new", "Second frame", "--json")
    slug = json.loads(second.stdout)["slug"]
    # current pointer is now the second frame; ask about the first explicitly.
    proc = _drive(tmp_path, "status", "--frame", "first-frame")
    assert "frame: first-frame" in proc.stdout
    assert slug != "first-frame"  # guards the test against a no-op


def test_status_surfaces_real_frame_errors(tmp_path: Path) -> None:
    # A bad --frame must surface devague's error, not a misleading fallback.
    _drive(tmp_path, "new", "A real frame")
    proc = run("status", "--frame", "ghost", cwd=tmp_path)
    assert proc.returncode != 0
    assert "no such frame" in proc.stderr
    assert "no frames yet" not in proc.stdout
    assert "unknown" not in proc.stdout


def test_export_blocked_until_converged(tmp_path: Path) -> None:
    _drive(tmp_path, "new", "Devague ships a documented spec contract")
    proc = run("export", cwd=tmp_path)
    assert proc.returncode != 0
    assert "has not converged" in proc.stderr


def test_full_session_converges_and_exports(tmp_path: Path) -> None:
    _drive(tmp_path, "new", "Devague ships a documented spec contract")
    _drive(tmp_path, "capture", "--kind", "audience", "devague + the assisting LLM")
    _drive(tmp_path, "capture", "--kind", "after_state", "a vague idea becomes a buildable spec")
    _drive(tmp_path, "capture", "--kind", "why_it_matters", "specs converge on evidence not vibes")
    _drive(tmp_path, "capture", "--kind", "boundary", "not a full PRD generator")
    _drive(tmp_path, "capture", "--kind", "success_signal", "exports only after the gate passes")

    # Every confirmed spec-affecting claim needs a confirmed honesty condition.
    for cid in ("c1", "c2", "c3", "c4", "c5", "c6"):
        out = _drive(tmp_path, "interrogate", cid, "--honesty", f"{cid} is testable", "--json")
        hid = json.loads(out.stdout)["added"][0]["id"]
        _drive(tmp_path, "confirm", hid)

    status = _drive(tmp_path, "status")
    assert "PASSED" in status.stdout
    assert "devague export" in status.stdout

    _drive(tmp_path, "converge")
    exported = _drive(tmp_path, "export")
    assert "exported spec" in exported.stdout
    specs = list((tmp_path / "docs" / "specs").glob("*.md"))
    assert specs, "export should write a spec file"


def test_missing_cli_emits_install_hint(tmp_path: Path) -> None:
    """With no resolvable ``devague``/``uv`` and no checkout, the wrapper hints."""
    minimal_path = "/usr/bin:/bin"
    env = {**os.environ, "PATH": minimal_path}
    # Skip if this environment still resolves the tools under the minimal PATH.
    if shutil.which("devague", path=minimal_path) or shutil.which("uv", path=minimal_path):
        pytest.skip("devague/uv resolvable under minimal PATH; cannot test hint path")
    proc = run("show", cwd=tmp_path, env=env)
    assert proc.returncode != 0
    assert "devague CLI not found" in proc.stderr
