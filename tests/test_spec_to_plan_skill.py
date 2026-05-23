"""Smoke tests for the first-party ``spec-to-plan`` skill wrapper.

These drive ``.claude/skills/spec-to-plan/scripts/spec-to-plan.sh`` via subprocess
in a sandboxed ``tmp_path`` cwd (so ``.devague/`` never touches the repo). The
wrapper forwards every move to ``devague plan <move>`` verbatim and adds a
``status`` helper that reads the plan convergence gate. Frames are seeded with the
sibling ``think`` wrapper, since a plan must start from a converged frame. The
skill is named ``spec-to-plan``; the CLI it drives is ``devague plan``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "spec-to-plan" / "scripts" / "spec-to-plan.sh"
THINK = REPO_ROOT / ".claude" / "skills" / "think" / "scripts" / "think.sh"
_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _run(script: Path, *args: str, cwd: Path, env: dict | None = None):
    return subprocess.run(
        ["bash", str(script), *args], cwd=str(cwd), env=env, capture_output=True, text=True
    )


def run(*args: str, cwd: Path, env: dict | None = None):
    return _run(SCRIPT, *args, cwd=cwd, env=env)


def _drive(cwd: Path, *args: str):
    proc = run(*args, cwd=cwd)
    assert proc.returncode == 0, f"{args} failed: {proc.stderr}"
    return proc


def _think(cwd: Path, *args: str):
    proc = _run(THINK, *args, cwd=cwd)
    assert proc.returncode == 0, f"think {args} failed: {proc.stderr}"
    return proc


def _converged_frame(cwd: Path) -> str:
    out = _think(cwd, "new", "Ship the plan engine", "--json")
    slug = json.loads(out.stdout)["slug"]
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        _think(cwd, "capture", "--kind", kind, f"{kind} text", "--origin", "user")
    for cid in (f"c{i}" for i in range(1, 7)):
        _think(cwd, "interrogate", cid, "--honesty", f"{cid} is testable", "--origin", "user")
    return slug


def test_script_is_executable_and_valid_bash() -> None:
    assert SCRIPT.exists(), f"missing wrapper at {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), "wrapper should be executable"
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_help_lists_moves(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "help")
    assert "spec→plan engine" in proc.stdout
    for move in ("new", "task", "cover", "converge", "export", "status"):
        assert move in proc.stdout


def test_status_reports_no_plans(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "status")
    assert "no plans yet" in proc.stdout


def test_forwards_learn_verbatim(tmp_path: Path) -> None:
    proc = _drive(tmp_path, "learn")
    assert "buildable plan" in proc.stdout


def test_status_names_gaps_and_next_move(tmp_path: Path) -> None:
    slug = _converged_frame(tmp_path)
    _drive(tmp_path, "new", "--frame", slug)
    proc = _drive(tmp_path, "status")
    assert "NOT passed" in proc.stdout
    assert "no tasks yet" in proc.stdout
    assert "devague plan task" in proc.stdout  # first-gap suggestion


def test_new_refuses_unconverged_frame(tmp_path: Path) -> None:
    _think(tmp_path, "new", "just an idea")
    proc = run("new", "--frame", "just-an-idea", cwd=tmp_path)
    assert proc.returncode != 0
    assert "has not converged" in proc.stderr


def test_full_session_converges_and_exports(tmp_path: Path) -> None:
    slug = _converged_frame(tmp_path)
    _drive(tmp_path, "new", "--frame", slug)
    args = ["task", "Build everything", "--accept", "all targets satisfied"]
    for tid in _ALL_TARGETS:
        args += ["--covers", tid]
    _drive(tmp_path, *args)

    status = _drive(tmp_path, "status")
    assert "PASSED" in status.stdout
    assert "devague plan export" in status.stdout

    _drive(tmp_path, "converge")
    exported = _drive(tmp_path, "export")
    assert "exported plan" in exported.stdout
    plans = list((tmp_path / "docs" / "plans").glob("*.md"))
    assert plans, "export should write a plan file"


def test_missing_cli_emits_install_hint(tmp_path: Path) -> None:
    minimal_path = "/usr/bin:/bin"
    env = {**os.environ, "PATH": minimal_path}
    if shutil.which("devague", path=minimal_path) or shutil.which("uv", path=minimal_path):
        pytest.skip("devague/uv resolvable under minimal PATH; cannot test hint path")
    proc = run("show", cwd=tmp_path, env=env)
    assert proc.returncode != 0
    assert "devague CLI not found" in proc.stderr
