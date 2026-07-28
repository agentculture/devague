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


# ── t19: SKILL.md must describe the surface the CLI actually ships ────────────
#
# The moves table in this skill went stale across several releases: it still
# taught `plan reject` as single-id ("loop for batches") after devague#86 made
# it transactional and multi-id, and never gained `defer` (#85), `amend`,
# `deliverables`, `depend --remove`, or `risk --amend` (#84). That matters more
# here than in most docs: guildmaster re-broadcasts this skill to every repo in
# the mesh, so a stale instruction propagates the very workaround the release
# removed. These tests pin the skill text against the live CLI surface.

SKILL_MD = REPO_ROOT / ".claude" / "skills" / "spec-to-plan" / "SKILL.md"


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _moves_table_first_cells() -> str:
    """The first column of every row in the ``### Moves`` table, joined.

    Rows legitimately pack two moves into one cell (``show`` / ``list``,
    ``learn`` / ``explain``), so membership is checked against the whole
    first-column text rather than against a row prefix.
    """
    lines = _skill_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "### Moves")
    cells: list[str] = []
    for ln in lines[start:]:
        if not ln.startswith("|"):
            if cells:  # the table ended
                break
            continue
        cells.append(ln.split("|")[1])
    return "\n".join(cells)


def test_skill_md_exists() -> None:
    assert SKILL_MD.is_file()


@pytest.mark.parametrize(
    "move",
    [
        "new",
        "task",
        "instruct",
        "accept",
        "amend",
        "depend",
        "cover",
        "defer",
        "confirm",
        "reject",
        "risk",
        "converge",
        "export",
        "waves",
        "deliverables",
        "status",
        "show",
        "list",
        "learn",
        "explain",
    ],
)
def test_skill_md_moves_table_names_every_shipped_plan_move(move: str) -> None:
    # Every subcommand `devague plan --help` registers must appear in the
    # skill's Moves table, or an operator driving from the skill cannot reach it.
    cells = _moves_table_first_cells()
    assert f"`{move}" in cells, f"'{move}' missing from the SKILL.md moves table"


def test_skill_md_does_not_teach_the_single_id_reject_workaround() -> None:
    # devague#86: `plan confirm`/`plan reject` are transactional and multi-id.
    text = _skill_text()
    assert "one task id per call" not in text
    assert "loop for batches" not in text


def test_skill_md_documents_transactional_multi_id_confirm_reject() -> None:
    text = _skill_text()
    assert "transactional" in text
    assert "`confirm <tN> [<tN>…]`" in text


def test_skill_md_documents_defer_as_the_honest_scoping_move() -> None:
    # devague#85: the gate rewards a task that *mentions* a target it does not
    # deliver. The skill must point at `defer`, not at faking coverage.
    text = _skill_text()
    assert "defer" in text
    assert "Deferred targets" in text
    assert "out_of_scope` *risk* does **not** excuse a target" in text


def test_skill_md_documents_live_frame_cover_validation() -> None:
    # devague#90: `cover` validates against the live frame, not the seed snapshot.
    assert "live" in _skill_text().lower()
    assert "grew after seeding" in _skill_text()


def test_skill_md_documents_risk_amend() -> None:
    # devague#84 comment: a risk whose text names a rotated task id is amendable.
    assert "--amend <rN>" in _skill_text()
