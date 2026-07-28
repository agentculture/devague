from __future__ import annotations

from devague.frame import Frame
from devague.plan import CoverageTarget, Plan
from devague.render.plan_md import render_plan
from tests.test_render import assert_blanks_around_headings_and_lists


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


def test_plan_md_blanks_around_headings_and_lists() -> None:
    p = _plan()
    p.add_risk("scaling unknown", "unknown_blocking", task_id="t1")
    assert_blanks_around_headings_and_lists(render_plan(p, _frame()))


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


# ── #64: markdownlint-safe rendering (MD026 trailing-punctuation headings, ────
# MD034 bare URLs) ─────────────────────────────────────────────────────────────


def _hostile_plan_and_frame() -> tuple[Plan, Frame]:
    f = Frame(slug="hostile", title="Hostile plan frame")
    f.add_claim(
        "announcement",
        "League of Agents is live at https://league-of-agents.ai.",
        origin="user",
    )
    p = Plan(
        slug="hostile",
        title="Ship the beautiful, welcoming home page.",
        frame_slug="hostile",
    )
    t1 = p.add_task("Point DNS at https://league-of-agents.ai.")
    p.add_acceptance(t1, "site resolves at https://league-of-agents.ai.")
    p.add_cover(t1, "c1")
    p.add_risk(
        "traffic spike risk, see http://status.league-of-agents.ai for load.",
        "unknown_nonblocking",
        task_id="t1",
    )
    return p, f


def test_plan_md_title_heading_strips_trailing_period() -> None:
    out = render_plan(*_hostile_plan_and_frame())
    first_line = out.split("\n", 1)[0]
    assert first_line == "# Build Plan — Ship the beautiful, welcoming home page"
    assert not first_line.endswith(".")


def test_plan_md_task_heading_strips_trailing_period_and_wraps_url() -> None:
    out = render_plan(*_hostile_plan_and_frame())
    assert "### t1 — Point DNS at <https://league-of-agents.ai>\n" in out
    heading_line = next(ln for ln in out.split("\n") if ln.startswith("### t1"))
    assert not heading_line.endswith(".")


def test_plan_md_announcement_blockquote_keeps_period_but_wraps_url() -> None:
    out = render_plan(*_hostile_plan_and_frame())
    assert "> League of Agents is live at <https://league-of-agents.ai>." in out


def test_plan_md_wraps_url_in_acceptance_criterion() -> None:
    out = render_plan(*_hostile_plan_and_frame())
    assert "  - site resolves at <https://league-of-agents.ai>." in out


def test_plan_md_wraps_url_in_risk_text() -> None:
    out = render_plan(*_hostile_plan_and_frame())
    expected = (
        "- [unknown_nonblocking] traffic spike risk, see "
        "<http://status.league-of-agents.ai> for load. (task t1)"
    )
    assert expected in out


def test_plan_md_hostile_input_is_markdownlint_clean() -> None:
    assert_blanks_around_headings_and_lists(render_plan(*_hostile_plan_and_frame()))


def test_plan_md_does_not_mutate_plan_or_task_text() -> None:
    plan, frame = _hostile_plan_and_frame()
    before_title = plan.title
    before_summary = plan.tasks[0].summary
    render_plan(plan, frame)
    assert plan.title == before_title
    assert plan.tasks[0].summary == before_summary


# ── #85: Deferred targets section ────────────────────────────────────────────


def test_deferred_targets_section_names_target_and_reason() -> None:
    p = _plan()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    p.defer_target("c47", "Milestone 3: worktree mechanics")
    out = render_plan(p, _frame())
    assert "## Deferred targets" in out
    assert "`c47`" in out
    assert "worktree concurrency" in out
    assert "deferred: Milestone 3: worktree mechanics" in out


def test_no_deferred_targets_section_when_nothing_deferred() -> None:
    out = render_plan(_plan(), _frame())
    assert "## Deferred targets" not in out


def test_deferred_targets_section_lists_every_deferred_target() -> None:
    p = _plan()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="target A"))
    p.targets.append(CoverageTarget(id="h35", kind="honesty", text="target B"))
    p.defer_target("c47", "reason A")
    p.defer_target("h35", "reason B")
    out = render_plan(p, _frame())
    assert "`c47`" in out and "reason A" in out
    assert "`h35`" in out and "reason B" in out


def test_deferred_targets_section_blanks_around_headings_and_lists() -> None:
    p = _plan()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="target A"))
    p.defer_target("c47", "reason A")
    assert_blanks_around_headings_and_lists(render_plan(p, _frame()))


# ── #87 MD050 regression: underscore-bearing verbatim text (t9) ─────────────


def test_task_heading_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.add_task("no functional export is added to shell/fs/__init__.py")
    out = render_plan(p, None)
    heading_line = next(ln for ln in out.split("\n") if ln.startswith("### t1"))
    assert "shell/fs/`__init__.py`" in heading_line
    # never a bare, unwrapped dunder in the heading (the MD050 trigger).
    assert "__init__.py" not in heading_line.replace("`__init__.py`", "")


def test_task_instruction_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t = p.add_task("core")
    t.instruction = "calls _read_file directly"
    out = render_plan(p, None)
    assert "- instruction: calls `_read_file` directly" in out


def test_acceptance_criterion_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t = p.add_task("core")
    p.add_acceptance(t, "_read_file and __init__.py both matter")
    out = render_plan(p, None)
    assert "  - `_read_file` and `__init__.py` both matter" in out


def test_risk_text_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.add_risk("touches shell/fs/__init__.py directly", "unknown_nonblocking")
    out = render_plan(p, None)
    assert "shell/fs/`__init__.py`" in out


def test_deferred_target_reason_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets.append(CoverageTarget(id="c1", kind="requirement", text="x"))
    p.defer_target("c1", "belongs to shell/fs/__init__.py migration")
    out = render_plan(p, None)
    assert "shell/fs/`__init__.py`" in out


def test_plan_title_wraps_underscore_identifier() -> None:
    p = Plan(slug="demo", title="Ship the __init__.py rewrite", frame_slug="demo")
    out = render_plan(p, None)
    assert out.startswith("# Build Plan — Ship the `__init__.py` rewrite")


def test_underscore_bearing_plan_blanks_around_headings_and_lists() -> None:
    """The full MD050-regression shape in one plan, run through the same blank-line
    structural check the hostile-URL tests already use — the closest in-repo proxy
    for "passes markdownlint-cli2" without shelling out to the linter itself."""
    p = Plan(slug="demo", title="Ship the __init__.py rewrite", frame_slug="demo")
    t = p.add_task("no functional export is added to shell/fs/__init__.py")
    t.instruction = "calls _read_file directly"
    p.add_acceptance(t, "_read_file and __init__.py both matter")
    p.targets.append(CoverageTarget(id="c1", kind="requirement", text="x"))
    p.defer_target("c1", "belongs to shell/fs/__init__.py migration")
    p.add_risk("touches shell/fs/__init__.py directly", "unknown_nonblocking")
    assert_blanks_around_headings_and_lists(render_plan(p, None))
