from __future__ import annotations

from devague.frame import Frame
from devague.plan import Plan
from devague.render.plan_md import render_plan


def _frame() -> Frame:
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "We shipped the plan engine", origin="user")
    return f


def _plan() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t1 = p.add_task("foundation")
    p.add_acceptance(t1, "core lands")
    p.add_cover(t1, "c1")
    t2 = p.add_task("on top")
    p.add_dep(t2, "t1")
    p.add_cover(t2, "h1")
    return p


def test_topo_order_places_dep_before_dependent() -> None:
    # t2 depends on t1; even if stored t1 first, dependents must follow deps.
    out = render_plan(_plan(), _frame())
    assert out.index("### t1") < out.index("### t2")


def test_acceptance_and_covers_rendered() -> None:
    out = render_plan(_plan(), _frame())
    assert "- covers: c1" in out
    assert "- acceptance:" in out and "  - core lands" in out
    assert "- depends on: t1" in out


def test_announcement_blockquote_from_frame() -> None:
    out = render_plan(_plan(), _frame())
    assert "> We shipped the plan engine" in out


def test_renders_without_frame() -> None:
    out = render_plan(_plan(), None)
    assert out.startswith("# Build Plan — Demo")
    assert ">" not in out.split("## Tasks")[0]


def test_risks_section() -> None:
    p = _plan()
    p.add_risk("scaling unknown", "unknown_blocking", task_id="t1")
    out = render_plan(p, _frame())
    assert "## Risks" in out
    assert "- [unknown_blocking] scaling unknown (task t1)" in out


def test_rejected_task_omitted() -> None:
    p = _plan()
    p.set_status("t2", "rejected")
    out = render_plan(p, _frame())
    assert "### t2" not in out


def test_cycle_still_renders() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    a = p.add_task("a")
    b = p.add_task("b")
    p.add_dep(a, "t2")
    p.add_dep(b, "t1")
    out = render_plan(p, None)  # cycle: must not raise, both tasks appear
    assert "### t1" in out and "### t2" in out
