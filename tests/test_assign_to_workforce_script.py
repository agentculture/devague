"""#69 t5 integration test: assign-to-workforce.sh split-plan's 4-column table.

A human reviewing a 13-task fan-out rewrote the split-plan table by hand as
Wave, Task, Model, Task summary — and that hand-rewrite is what got approved
(agentculture/devague#69). This test drives the real script end to end
(``bash assign-to-workforce.sh split-plan``) against a fixture plan built via
the actual ``devague`` / ``devague plan`` CLI (more robust than hand-writing
``.devague`` JSON), and asserts the table the human actually approves comes
out: exactly one four-column table (Wave | Task | Model | Task summary),
rows ordered by wave then task id, real (never placeholder) summaries
truncated with an ellipsis past 72 chars, a `sonnet` default model, the
has-instruction/acceptance-count markers moved onto the wave-listing lines,
and the go/no-go prompt + fan-out steps still present.

The script resolves its own ``devague`` binary (mesh-first: whatever is on
PATH, falling back to `uv run` inside a devague checkout). To make this test
hermetic — exercising *this* worktree's code rather than whatever `devague`
happens to be installed globally — a small PATH shim forwards to
``uv run --project <this-repo> devague`` regardless of cwd.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import store
from devague.cli import main

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = (
    _REPO_ROOT / ".claude" / "skills" / "assign-to-workforce" / "scripts" / "assign-to-workforce.sh"
)

_BASH = shutil.which("bash")
_UV = shutil.which("uv")

pytestmark = pytest.mark.skipif(
    _BASH is None or _UV is None,
    reason="bash/uv not on PATH (the script + this test's local-devague shim both need them)",
)

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")

# Deliberately > 72 chars, to exercise ellipsis truncation in the summary cell.
_LONG_SUMMARY = (
    "Reshape the per-task split-plan table to exactly Wave, Task, Model, and "
    "Task summary columns for human review"
)
assert len(_LONG_SUMMARY) > 72

_MAX_SUMMARY_LEN = 72
_ELLIPSIS = "..."
_EXPECTED_TRUNCATED = _LONG_SUMMARY[:_MAX_SUMMARY_LEN] + _ELLIPSIS


def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the split-plan table"])
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _fixture_plan(monkeypatch, tmp_path) -> str:
    """An in-progress plan (waves are read-only + convergence-agnostic, #20):

    - t1: short summary, an instruction, 2 acceptance criteria, no deps -> wave 1.
    - t3: short summary, no instruction, 1 acceptance criterion, no deps -> wave 1
      (created after t2 so wave-1 ordering — t1 before t3 — matches id order too).
    - t2: a >72-char summary, no instruction, 0 acceptance criteria, depends on
      t1 -> wave 2.
    """
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(
        [
            "plan",
            "task",
            "Wire the login form",
            "--instruction",
            "verify via `pytest`",
            "--accept",
            "form submits",
            "--accept",
            "errors render",
        ]
    )
    main(["plan", "task", _LONG_SUMMARY, "--dep", "t1"])
    main(["plan", "task", "Send the welcome email", "--accept", "email delivered"])
    return slug


def _devague_shim(tmp_path: Path) -> Path:
    """A `devague` PATH shim that always runs *this* worktree's checkout via
    `uv run`, regardless of cwd — so the script under test exercises this
    branch's code, never a possibly stale globally installed `devague`.
    """
    bin_dir = tmp_path / "_bin"
    bin_dir.mkdir(exist_ok=True)
    shim = bin_dir / "devague"
    shim.write_text(
        "#!/usr/bin/env bash\n" f'exec "{_UV}" run --project "{_REPO_ROOT}" devague "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return bin_dir


def _run_split_plan(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bin_dir = _devague_shim(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_BASH, str(_SCRIPT), "split-plan"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_split_plan_renders_expected_table(tmp_path, monkeypatch) -> None:
    _fixture_plan(monkeypatch, tmp_path)
    result = _run_split_plan(tmp_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    out = result.stdout
    lines = out.splitlines()

    def _cells(line: str) -> list[str]:
        # "| 1    | t1   | sonnet | ... |" -> ["1", "t1", "sonnet", "..."]
        return [c.strip() for c in line.strip().strip("|").split("|")]

    # ── exactly one table, with the exact 4-column header ───────────────────
    # Column widths pad to the widest cell (e.g. "sonnet" > "Model"), so match
    # on the parsed header cells rather than a hard-coded spacing literal.
    header_indices = [
        i
        for i, line in enumerate(lines)
        if line.startswith("|") and _cells(line) == ["Wave", "Task", "Model", "Task summary"]
    ]
    assert len(header_indices) == 1
    header_idx = header_indices[0]
    sep_idx = header_idx + 1
    assert set(lines[sep_idx].replace("|", "").strip()) <= {"-", " "}

    # ── rows ordered by wave then task id ────────────────────────────────────
    def _row_idx(task_id: str) -> int:
        return next(
            i
            for i, line in enumerate(lines)
            if i > header_idx and line.startswith("|") and _cells(line)[1] == task_id
        )

    t1_idx, t3_idx, t2_idx = _row_idx("t1"), _row_idx("t3"), _row_idx("t2")
    assert header_idx < t1_idx < t3_idx < t2_idx

    # ── real summaries, never a placeholder; sonnet default per row ─────────
    assert _cells(lines[t1_idx])[3] == "Wire the login form"
    assert _cells(lines[t3_idx])[3] == "Send the welcome email"
    assert "(no summary recorded)" not in out
    for idx in (t1_idx, t3_idx, t2_idx):
        assert _cells(lines[idx])[2] == "sonnet"
    assert _cells(lines[t1_idx])[0] == "1"
    assert _cells(lines[t3_idx])[0] == "1"
    assert _cells(lines[t2_idx])[0] == "2"

    # ── truncation with ellipsis for the >72-char summary ────────────────────
    # The table truncates; the End state section (#70 t6) below it quotes
    # `devague plan deliverables` verbatim, which legitimately reproduces the
    # full untruncated summary for a terminal task — so this check is scoped
    # to the split-plan table's own region of the output, not the full text.
    table_out = out[: out.index(_END_STATE_HEADER)] if _END_STATE_HEADER in out else out
    assert _LONG_SUMMARY not in table_out
    assert _cells(lines[t2_idx])[3] == _EXPECTED_TRUNCATED

    # ── wave-listing markers (moved off the table, #69) ──────────────────────
    assert "t1 [instruction: yes, accept: 2]" in out
    assert "t3 [instruction: no, accept: 1]" in out
    assert "t2 [instruction: no, accept: 0]" in out
    assert "Wave 1: [t1 [instruction: yes, accept: 2], t3 [instruction: no, accept: 1]]" in out
    assert "Wave 2: [t2 [instruction: no, accept: 0]]" in out

    # ── go/no-go prompt + fan-out steps survive ──────────────────────────────
    assert "Go/no-go" in out
    assert "Approved — assign to workforce" in out
    assert "Create one git worktree per task" in out

    # ── operator guidance to edit the Model cell to a real model token ───────
    assert "haiku" in out and "sonnet" in out and "opus" in out and "fable" in out
    assert "colleague" in out or "codex" in out


def test_split_plan_table_has_no_agent_type_or_scope_note_columns(tmp_path, monkeypatch) -> None:
    """The old 8-column shape (Agent type / Scope note, etc.) must be gone."""
    _fixture_plan(monkeypatch, tmp_path)
    result = _run_split_plan(tmp_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    out = result.stdout
    assert "Agent type" not in out
    assert "Scope note" not in out
    assert "cheaper/faster" not in out


# ── End state section: `devague plan deliverables`, verbatim (#70 t6) ───────
#
# At the go/no-go, the human should see what the plan actually produces —
# `devague plan deliverables` synthesizes that "what do we have in the end?"
# view from live frame/plan state (confirmed after-state claims, terminal
# tasks, surviving open items). split-plan quotes it verbatim, never composing
# it freehand, and degrades to a one-line hint on a `devague` too old to have
# the verb — never failing the script.

_END_STATE_HEADER = "End state (from `devague plan deliverables`):"
_DEGRADED_HINT = "hint: End state view requires devague >= 0.18.0 (devague plan deliverables)"


def _devague_shim_without_deliverables(tmp_path: Path) -> Path:
    """A `devague` PATH shim that behaves like this worktree's checkout for
    every verb except `plan deliverables`, which it rejects with a non-zero
    exit — simulating an older devague that predates the deliverables view
    (#70), to exercise split-plan's graceful degradation.
    """
    bin_dir = tmp_path / "_bin_old"
    bin_dir.mkdir(exist_ok=True)
    shim = bin_dir / "devague"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "plan" ] && [ "$2" = "deliverables" ]; then\n'
        "    exit 2\n"
        "fi\n"
        f'exec "{_UV}" run --project "{_REPO_ROOT}" devague "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return bin_dir


def test_split_plan_ends_with_end_state_section(tmp_path, monkeypatch) -> None:
    """split-plan's output ends with an End state section that is exactly the
    verbatim `devague plan deliverables` output for the same fixture plan."""
    _fixture_plan(monkeypatch, tmp_path)
    result = _run_split_plan(tmp_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    out = result.stdout

    bin_dir = _devague_shim(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    deliverables = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [str(bin_dir / "devague"), "plan", "deliverables"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert deliverables.returncode == 0, deliverables.stderr

    assert _END_STATE_HEADER in out
    # It is the LAST section split-plan prints — after the go/no-go + fan-out
    # steps, never before them.
    header_idx = out.index(_END_STATE_HEADER)
    assert header_idx > out.index("Create one git worktree per task")
    tail = out[header_idx + len(_END_STATE_HEADER) :]
    assert tail.strip("\n") == deliverables.stdout.rstrip("\n")


def test_split_plan_degrades_gracefully_without_deliverables_verb(tmp_path, monkeypatch) -> None:
    """On an older devague lacking `plan deliverables`, split-plan still exits
    0 and prints a one-line hint naming the minimum version instead of
    failing."""
    _fixture_plan(monkeypatch, tmp_path)
    bin_dir = _devague_shim_without_deliverables(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_BASH, str(_SCRIPT), "split-plan"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    out = result.stdout

    assert _DEGRADED_HINT in out
    assert _END_STATE_HEADER not in out
    # The rest of the split plan still renders — degradation must not take
    # down the whole command.
    assert "Go/no-go" in out
    assert "Create one git worktree per task" in out
