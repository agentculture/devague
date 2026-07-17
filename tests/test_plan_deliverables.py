"""Tests for #53-esd t2: the read-only ``devague plan deliverables`` view (#70).

Answers "what do we have in the end?" at the assign-to-workforce go/no-go, sourced
only from existing frame/plan state: the live source frame's confirmed
``announcement`` / ``after_state`` / ``success_signal`` claims (verbatim), the
plan's terminal tasks (active tasks no other active task depends on) with their
acceptance criteria, and surviving open items (the frame's non-blocking parked
vagueness plus the plan's non-blocking risks). Covers all three acceptance criteria:

1. a converged plan prints the world-after claims, terminal tasks + acceptance
   criteria, and surviving parked items — in both text and ``--json``.
2. an unconverged plan renders with an explicit not-converged banner / ``converged:
   false`` — it never refuses.
3. two consecutive renders leave ``.devague/`` byte-identical (read-only proof).
"""

from __future__ import annotations

import json
from pathlib import Path

from devague import store
from devague.cli import main
from devague.plan import Plan, Task, terminal_tasks
from devague.render.deliverables_md import NOT_CONVERGED_BANNER, render_deliverables
from tests.test_render import assert_blanks_around_headings_and_lists

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")
_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


# ── pure unit tests: terminal_tasks (devague/plan.py) ────────────────────────
def _task(tid: str, deps: list[str] | None = None, status: str = "confirmed") -> Task:
    return Task(id=tid, summary=f"summary {tid}", status=status, deps=list(deps or []))


def test_terminal_tasks_empty() -> None:
    assert terminal_tasks([]) == []


def test_terminal_tasks_single_task_with_no_deps_is_terminal() -> None:
    t1 = _task("t1")
    assert terminal_tasks([t1]) == [t1]


def test_terminal_tasks_excludes_a_task_something_else_depends_on() -> None:
    t1 = _task("t1")
    t2 = _task("t2", deps=["t1"])
    assert terminal_tasks([t1, t2]) == [t2]


def test_terminal_tasks_diamond_only_the_sink_is_terminal() -> None:
    t1 = _task("t1")
    t2 = _task("t2", deps=["t1"])
    t3 = _task("t3", deps=["t1"])
    t4 = _task("t4", deps=["t2", "t3"])
    assert terminal_tasks([t1, t2, t3, t4]) == [t4]


def test_terminal_tasks_rejected_dependent_frees_its_dependency() -> None:
    # t2 depends on t1 but is itself rejected — t2 is never terminal (rejected is
    # excluded), and it no longer "uses up" t1's terminal status either.
    t1 = _task("t1")
    t2 = _task("t2", deps=["t1"], status="rejected")
    assert terminal_tasks([t1, t2]) == [t1]


def test_terminal_tasks_stable_stored_order() -> None:
    t1 = _task("t1")
    t2 = _task("t2")
    t3 = _task("t3")
    assert terminal_tasks([t3, t1, t2]) == [t3, t1, t2]


# ── pure unit tests: render_deliverables (devague/render/deliverables_md.py) ──
def _frame_with_world_after():
    from devague.frame import Frame

    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "We shipped X", origin="user")
    f.add_claim("after_state", "Users can do Y", origin="user")
    f.add_claim("success_signal", "95% success rate", origin="user")
    f.add_claim("audience", "operators", origin="user")  # NOT part of the world-after view
    f.add_vagueness("scale unknown", "unknown_nonblocking")
    f.add_vagueness("a real blocker", "unknown_blocking")  # must never survive
    return f


def _plan_with_tasks() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t1 = p.add_task("foundation")
    p.add_acceptance(t1, "core lands")
    t2 = p.add_task("on top")
    p.add_dep(t2, "t1")
    p.add_acceptance(t2, "integration works")
    p.add_risk("perf unknown", "unknown_nonblocking", task_id="t2")
    p.add_risk("a blocking risk", "unknown_blocking", task_id="t2")  # must never survive
    return p


def test_render_deliverables_converged_has_no_banner() -> None:
    out = render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=True)
    assert NOT_CONVERGED_BANNER not in out


def test_render_deliverables_world_after_verbatim() -> None:
    out = render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=True)
    assert "## Announcement" in out and "We shipped X" in out
    assert "## After state" in out and "Users can do Y" in out
    assert "## Success signals" in out and "95% success rate" in out
    assert "operators" not in out  # audience is not one of the three world-after kinds


def test_render_deliverables_terminal_tasks_only() -> None:
    out = render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=True)
    assert "## Terminal tasks" in out
    assert "`t2`" in out and "on top" in out
    assert "integration works" in out
    assert "`t1`" not in out  # t1 is not terminal — t2 depends on it
    assert "foundation" not in out


def test_render_deliverables_open_items_excludes_blocking() -> None:
    out = render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=True)
    assert "## Open items" in out
    assert "[unknown_nonblocking] scale unknown" in out
    assert "[unknown_nonblocking] perf unknown" in out
    assert "a real blocker" not in out
    assert "a blocking risk" not in out


# ── resolve-parked-vagueness (#53-esd t7): surviving-open-items excludes ─────
# resolved frame vagueness and resolved plan risks ───────────────────────────


def test_render_deliverables_open_items_excludes_resolved_vagueness_and_risk() -> None:
    frame = _frame_with_world_after()
    plan = _plan_with_tasks()
    v = next(v for v in frame.open_vagueness if v.kind == "unknown_nonblocking")
    frame.resolve_vagueness(v.id, "decided: acceptable for v1")
    r = next(r for r in plan.risks if r.kind == "unknown_nonblocking")
    plan.resolve_risk(r.id, "mitigated by t2's retry logic")

    out = render_deliverables(plan, frame, converged=True)
    # both surviving non-blocking items are now resolved — nothing left to show.
    assert "## Open items" not in out
    assert "scale unknown" not in out
    assert "perf unknown" not in out


def test_render_deliverables_open_items_partial_resolution_keeps_unresolved() -> None:
    frame = _frame_with_world_after()
    plan = _plan_with_tasks()
    v = next(v for v in frame.open_vagueness if v.kind == "unknown_nonblocking")
    frame.resolve_vagueness(v.id, "decided: acceptable for v1")
    # the plan risk stays unresolved.

    out = render_deliverables(plan, frame, converged=True)
    assert "## Open items" in out
    assert "scale unknown" not in out  # resolved frame vagueness — excluded
    assert "[unknown_nonblocking] perf unknown" in out  # unresolved risk — still shown


def test_render_deliverables_resolved_blocking_items_still_excluded() -> None:
    # A resolved unknown_blocking item was already excluded by kind alone; confirm
    # resolving it doesn't somehow surface it (it must stay excluded either way).
    frame = _frame_with_world_after()
    plan = _plan_with_tasks()
    blocker = next(v for v in frame.open_vagueness if v.kind == "unknown_blocking")
    frame.resolve_vagueness(blocker.id, "decided: not a real blocker after all")
    risk_blocker = next(r for r in plan.risks if r.kind == "unknown_blocking")
    plan.resolve_risk(risk_blocker.id, "decided: mitigated")

    out = render_deliverables(plan, frame, converged=True)
    assert "a real blocker" not in out
    assert "a blocking risk" not in out


def test_render_deliverables_banner_when_not_converged() -> None:
    out = render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=False)
    lines = out.splitlines()
    assert lines[0] == "# Deliverables — Demo"
    assert lines[1] == ""
    assert lines[2] == NOT_CONVERGED_BANNER


def test_render_deliverables_omits_empty_sections() -> None:
    from devague.frame import Frame

    out = render_deliverables(
        Plan(slug="d", title="D", frame_slug="d"), Frame(slug="d", title="D"), converged=True
    )
    assert "## Announcement" not in out
    assert "## After state" not in out
    assert "## Success signals" not in out
    assert "## Terminal tasks" not in out
    assert "## Open items" not in out


def test_render_deliverables_markdownlint_clean() -> None:
    assert_blanks_around_headings_and_lists(
        render_deliverables(_plan_with_tasks(), _frame_with_world_after(), converged=False)
    )


# ── CLI fixtures ──────────────────────────────────────────────────────────────
def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the deliverables view"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys) -> str:
    """A converged plan with two tasks (t2 depends on t1, so only t2 is terminal),
    a surviving non-blocking parked frame vagueness, and a surviving non-blocking
    plan risk.
    """
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["park", "scale unknown", "--kind", "unknown_nonblocking"])
    main(["plan", "new", "--frame", slug])
    half, rest = _ALL_TARGETS[:6], _ALL_TARGETS[6:]
    args1 = ["plan", "task", "foundation work", "--accept", "foundation criteria met"]
    for tid in half:
        args1 += ["--covers", tid]
    main(args1)  # t1
    args2 = [
        "plan",
        "task",
        "integration work",
        "--accept",
        "integration criteria met",
        "--dep",
        "t1",
    ]
    for tid in rest:
        args2 += ["--covers", tid]
    main(args2)  # t2, depends on t1
    main(["plan", "risk", "perf unknown", "--kind", "unknown_nonblocking"])
    capsys.readouterr()
    return slug


def _devague_snapshot(root: Path) -> dict[str, bytes]:
    base = root / ".devague"
    if not base.exists():
        return {}
    return {
        str(p.relative_to(base)): p.read_bytes() for p in sorted(base.rglob("*")) if p.is_file()
    }


# ── acceptance criterion 1: converged plan, text + json ──────────────────────
def test_deliverables_converged_text(tmp_path, monkeypatch, capsys) -> None:
    _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "deliverables"])
    assert rc == 0
    out = capsys.readouterr().out
    assert NOT_CONVERGED_BANNER not in out
    assert "Ship the deliverables view" in out  # announcement, verbatim
    assert "after_state text" in out
    assert "success_signal text" in out
    assert "audience text" not in out  # audience is not a world-after kind
    assert "before_state text" not in out
    assert "boundary text" not in out
    assert "## Terminal tasks" in out
    assert "integration work" in out and "integration criteria met" in out
    assert "foundation work" not in out  # t1 is not terminal (t2 depends on it)
    assert "## Open items" in out
    assert "scale unknown" in out
    assert "perf unknown" in out


def test_deliverables_converged_json(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "deliverables", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert payload["converged"] is True
    assert payload["announcement"] == ["Ship the deliverables view"]
    assert payload["after_state"] == ["after_state text"]
    assert payload["success_signal"] == ["success_signal text"]
    ids = {t["id"] for t in payload["terminal_tasks"]}
    assert ids == {"t2"}
    (terminal_entry,) = payload["terminal_tasks"]
    assert terminal_entry["summary"] == "integration work"
    assert terminal_entry["acceptance_criteria"] == ["integration criteria met"]
    open_pairs = {(i["kind"], i["text"]) for i in payload["open_items"]}
    assert ("unknown_nonblocking", "scale unknown") in open_pairs
    assert ("unknown_nonblocking", "perf unknown") in open_pairs


# ── acceptance criterion 2: unconverged plan renders, never refuses ──────────
def test_deliverables_not_converged_renders_banner_and_never_refuses(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])  # no tasks yet — plan gate fails
    capsys.readouterr()

    rc = main(["plan", "deliverables"])
    assert rc == 0  # never refuses
    out = capsys.readouterr().out
    assert NOT_CONVERGED_BANNER in out
    assert "Ship the deliverables view" in out  # world-after still shows
    assert "## Terminal tasks" not in out  # no tasks at all

    rc = main(["plan", "deliverables", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["converged"] is False
    assert payload["announcement"] == ["Ship the deliverables view"]
    assert payload["terminal_tasks"] == []


def test_deliverables_excludes_blocking_items(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    # Park the blocker on the frame *after* seeding the plan — parking a blocking
    # vagueness un-converges the frame itself, which would otherwise refuse
    # `plan new` (deliverables must still survive this, per the frame-regression
    # test below, but there is no need to entangle the two here).
    main(["park", "a real blocker", "--kind", "unknown_blocking"])
    main(["plan", "risk", "a blocking risk", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["plan", "deliverables", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = {i["text"] for i in payload["open_items"]}
    assert "a real blocker" not in texts
    assert "a blocking risk" not in texts


def test_deliverables_survives_frame_regression(tmp_path, monkeypatch, capsys) -> None:
    # Unlike `plan status`/`plan converge`/`plan export`, deliverables must not
    # refuse even when the source frame itself has regressed below its own
    # convergence gate — it is a preview, not a gated move (#20).
    _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys)
    main(["reject", "c2"])  # drop a required confirmed claim -> frame un-converges
    capsys.readouterr()
    rc = main(["plan", "deliverables"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Ship the deliverables view" in out


def test_deliverables_missing_source_frame_still_errors(tmp_path, monkeypatch, capsys) -> None:
    # There is nothing at all to synthesize from — a different failure than
    # "not converged yet", so this is the one case deliverables does refuse.
    slug = _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys)
    store.path_for(slug).unlink()
    capsys.readouterr()
    rc = main(["plan", "deliverables"])
    assert rc == 1
    assert "no longer exists" in capsys.readouterr().err


def test_deliverables_registered_in_learn_and_explain(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "learn", "--json"]) == 0
    moves = json.loads(capsys.readouterr().out)["moves"]
    assert "deliverables" in moves
    assert main(["plan", "explain", "deliverables", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "deliverables"


# ── acceptance criterion 3: .devague/ stays byte-identical (read-only proof) ──
def test_deliverables_never_mutates_devague_state(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan_with_terminal_split(monkeypatch, tmp_path, capsys)
    before = _devague_snapshot(tmp_path)
    assert before  # sanity: there IS state to protect

    main(["plan", "deliverables"])
    main(["plan", "deliverables", "--json"])
    main(["plan", "deliverables"])
    main(["plan", "deliverables", "--json"])

    after = _devague_snapshot(tmp_path)
    assert before == after
    from devague import plan_store

    assert plan_store.load(slug).status == "drafting"  # converge was never persisted


def test_deliverables_never_mutates_devague_state_when_not_converged(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    before = _devague_snapshot(tmp_path)

    main(["plan", "deliverables"])
    main(["plan", "deliverables", "--json"])

    after = _devague_snapshot(tmp_path)
    assert before == after
