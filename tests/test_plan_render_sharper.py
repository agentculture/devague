"""Sharper plan renderer + enriched waves payload (#53 t9).

Covers c12 (plan-md renders a task's instruction verbatim), c11 (sharper exports —
the plan-md peer of t6's spec-md/frame-md instruction blocks), h3 (an absent
instruction renders nothing — never fabricated filler), c8 (a subagent brief needs
no external context — ``plan waves --json`` now carries summary/instruction/
acceptance/covers per task), and h12 (checkable on artifacts alone).

``render/plan_md.py`` gained a per-task ``- instruction: <verbatim text>`` bullet —
the plan-md idiom mirroring t6's nested ``- instruction:`` bullet in spec_md.py /
frame_md.py, adapted to a task (a heading, not a claim bullet): the instruction
renders as the first body bullet, immediately under the task heading, before
``depends on`` / ``covers`` / ``acceptance``. Absent entirely when the task carries
none. ``devague plan waves --json`` gained a top-level ``"tasks"`` key — an object
keyed by task id with ``{summary, instruction, acceptance_criteria, covers}`` for
every active (non-rejected) task appearing in ``waves`` — while keeping the existing
``plan`` and ``waves`` keys byte-compatible.
"""

from __future__ import annotations

import json
from pathlib import Path

from devague import plan_store, store
from devague.cli import main
from devague.frame import Frame
from devague.plan import Plan
from devague.render.plan_md import render_plan
from tests.test_render import assert_markdownlint_clean

GOLDENS = Path(__file__).parent / "goldens"


def _bare_frame() -> Frame:
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "We shipped the plan engine", origin="user")
    return f


def _bare_plan() -> Plan:
    """A plan with no task instructions — the pre-t9 shape."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t1 = p.add_task("foundation")
    p.add_acceptance(t1, "core lands")
    p.add_cover(t1, "c1")
    t2 = p.add_task("on top")
    p.add_dep(t2, "t1")
    p.add_cover(t2, "h1")
    return p


# Captured from the renderer before t9 (git show HEAD:devague/render/plan_md.py
# against `_bare_plan()` / `_bare_frame()`) — locks in that the no-instruction path
# stays byte-identical.
_BARE_PLAN_BASELINE = (
    "# Build Plan — Demo\n"
    "\n"
    "slug: `demo` · status: `drafting` · from frame: `demo`\n"
    "\n"
    "> We shipped the plan engine\n"
    "\n"
    "## Tasks\n"
    "\n"
    "### t1 — foundation\n"
    "\n"
    "- covers: c1\n"
    "- acceptance:\n"
    "  - core lands\n"
    "\n"
    "### t2 — on top\n"
    "\n"
    "- depends on: t1\n"
    "- covers: h1\n"
)


def test_no_instruction_plan_md_byte_identical_to_baseline() -> None:
    assert render_plan(_bare_plan(), _bare_frame()) == _BARE_PLAN_BASELINE


def _sharper_frame() -> Frame:
    f = Frame(slug="sharper-plan", title="Sharper Plan Golden")
    f.add_claim("announcement", "we shipped the sharper plan renderer", origin="user")
    return f


def _sharper_plan() -> Plan:
    """A plan exercising a task instruction (t1) and a task with none (t2)."""
    p = Plan(slug="sharper-plan", title="Sharper Plan Golden", frame_slug="sharper-plan")
    t1 = p.add_task("lay the foundation")
    t1.instruction = "run `uv run pytest tests/test_plan.py -v` and confirm it is green"
    p.add_acceptance(t1, "foundation lands")
    p.add_cover(t1, "c1")
    t2 = p.add_task("build on top")
    p.add_dep(t2, "t1")
    p.add_cover(t2, "h1")
    # t2 carries no instruction — must render nothing.
    return p


def test_task_instruction_rendered_verbatim() -> None:
    out = render_plan(_sharper_plan(), _sharper_frame())
    assert "- instruction: run `uv run pytest tests/test_plan.py -v` and confirm it is green" in out


def test_task_without_instruction_has_no_instruction_line() -> None:
    out = render_plan(_sharper_plan(), _sharper_frame())
    lines = out.splitlines()
    idx = lines.index("### t2 — build on top")
    # t2's body starts on the next non-blank line; it must not be an instruction bullet.
    body_start = idx + 2  # skip the heading and the blank line after it
    assert not lines[body_start].strip().startswith("- instruction:")


def test_instruction_precedes_depends_covers_acceptance() -> None:
    out = render_plan(_sharper_plan(), _sharper_frame())
    lines = out.splitlines()
    idx = lines.index("### t1 — lay the foundation")
    assert lines[idx + 2].startswith("- instruction:")
    assert lines[idx + 3] == "- covers: c1"
    assert lines[idx + 4] == "- acceptance:"


def test_sharper_plan_md_is_markdownlint_clean() -> None:
    assert_markdownlint_clean(render_plan(_sharper_plan(), _sharper_frame()))


def test_golden_plan_md() -> None:
    expected = (GOLDENS / "sharper_plan.md").read_text(encoding="utf-8")
    assert render_plan(_sharper_plan(), _sharper_frame()) == expected


# ── waves --json enriched payload (#53 t9, c8/c11/h12) ───────────────────────────
_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")
_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _converged_frame(monkeypatch, tmp_path) -> str:
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the sharper plan renderer"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def test_waves_json_carries_tasks_payload(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(
        [
            "plan",
            "task",
            "Build everything",
            "--accept",
            "all targets satisfied",
            "--instruction",
            "run the full suite and diff the export",
            *[flag for tid in _ALL_TARGETS for flag in ("--covers", tid)],
        ]
    )
    capsys.readouterr()
    assert main(["plan", "waves", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # Existing keys stay byte-compatible.
    assert payload["plan"] == slug
    assert payload["waves"] == [["t1"]]
    # New "tasks" key: every field verbatim for the task in the waves.
    assert payload["tasks"] == {
        "t1": {
            "summary": "Build everything",
            "instruction": "run the full suite and diff the export",
            "acceptance_criteria": ["all targets satisfied"],
            "covers": _ALL_TARGETS,
        }
    }


def test_waves_json_tasks_without_instruction_is_empty_string(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "no instruction here"])
    capsys.readouterr()
    assert main(["plan", "waves", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tasks"]["t1"]["instruction"] == ""


def test_waves_json_tasks_excludes_rejected(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "task 1"])
    main(["plan", "task", "task 2"])
    main(["plan", "reject", "t2"])
    capsys.readouterr()
    assert main(["plan", "waves", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["tasks"].keys()) == {"t1"}
    assert "t2" not in payload["tasks"]


def test_waves_does_not_mutate_plan_state(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "task 1", "--instruction", "do it"])
    capsys.readouterr()
    before = plan_store.path_for(slug).read_text(encoding="utf-8")
    assert main(["plan", "waves", "--json"]) == 0
    assert plan_store.path_for(slug).read_text(encoding="utf-8") == before
