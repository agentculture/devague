"""Obligation rendering (bvts t4): frame_md and plan_md nest obligations under
their claim/task with a drift marker computed via the pure
``obligation_drift`` / ``criterion_obligation_drift`` functions — never
re-derived in the renderer. Mirrors the lapse ledger's rendering tests
(``tests/test_render_sharper.py``), but obligations render *nested* under
their owning claim/task rather than as a flat top-level section, since an
obligation is a per-claim/per-task commitment, not a frame/plan-wide ledger.

The exported spec-md must NOT gain an obligations section, exactly like the
lapse ledger (issue #97 t3) — the exported spec overwrites the same dated
file on every re-export, so execution-time obligations rendering there would
rewrite the what-to-build artifact.
"""

from __future__ import annotations

from devague.frame import Frame
from devague.plan import Plan
from devague.render.frame_md import render_frame
from devague.render.plan_md import render_plan
from devague.render.spec_md import render_spec
from tests.test_render import assert_markdownlint_clean

# ── frame_md ──────────────────────────────────────────────────────────────────


def _frame_with_claim() -> tuple[Frame, str]:
    f = Frame(slug="s", title="My Feature")
    c = f.add_claim("boundary", "scope is X only", origin="user")
    return f, c.id


def test_frame_md_omits_obligation_lines_when_none_filed() -> None:
    f, _ = _frame_with_claim()
    out = render_frame(f)
    assert "obligation:" not in out


def test_frame_md_renders_obligation_nested_under_its_claim() -> None:
    f, cid = _frame_with_claim()
    f.add_obligation(cid, "cli", "rejects bad input", origin="user")
    out = render_frame(f)
    assert "- scope is X only" in out
    assert "  - obligation: `o1` [cli] rejects bad input" in out
    assert "⚠ drifted" not in out


def test_frame_md_renders_proposed_obligation_status_marker() -> None:
    f, cid = _frame_with_claim()
    f.add_obligation(cid, "cli", "x", origin="llm")
    out = render_frame(f)
    assert "_(proposed)_" in out


def test_frame_md_renders_drift_marker_when_claim_text_changes() -> None:
    f, cid = _frame_with_claim()
    f.add_obligation(cid, "cli", "rejects bad input", origin="user")
    claim = f.find_claim(cid)
    claim.text = "scope now covers X and Y"
    out = render_frame(f)
    assert "⚠ drifted" in out


def test_frame_md_obligation_lines_are_markdownlint_clean() -> None:
    f, cid = _frame_with_claim()
    f.add_obligation(cid, "cli", "rejects bad input", origin="llm")
    assert_markdownlint_clean(render_frame(f))


def test_spec_md_never_renders_obligation_lines() -> None:
    f, cid = _frame_with_claim()
    f.add_obligation(cid, "cli", "rejects bad input", origin="user")
    out = render_spec(f)
    assert "obligation:" not in out
    assert "o1" not in out


def test_filing_obligations_does_not_change_render_spec_output() -> None:
    f, cid = _frame_with_claim()
    before = render_spec(f)
    f.add_obligation(cid, "cli", "rejects bad input", origin="user")
    f.add_obligation(cid, "store", "round-trips", origin="llm")
    after = render_spec(f)
    assert after == before


# ── plan_md ───────────────────────────────────────────────────────────────────


def _plan_with_task() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t = p.add_task("first task")
    p.add_acceptance(t, "criterion one")
    p.add_acceptance(t, "criterion two")
    return p


def test_plan_md_omits_obligation_lines_when_none_filed() -> None:
    p = _plan_with_task()
    out = render_plan(p, None)
    assert "obligation:" not in out


def test_plan_md_renders_obligation_nested_under_its_task() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input", origin="user")
    out = render_plan(p, None)
    assert "### t1 — first task" in out
    assert "- obligation: `o1` (criterion 1) [cli] rejects bad input" in out
    assert "⚠ drifted" not in out


def test_plan_md_renders_proposed_obligation_status_marker() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="x", origin="llm")
    out = render_plan(p, None)
    assert "_(proposed)_" in out


def test_plan_md_renders_drift_marker_when_criterion_text_changes() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input", origin="user")
    task = p.find_task("t1")
    task.acceptance_criteria[0] = "criterion one, revised"
    out = render_plan(p, None)
    assert "⚠ drifted" in out


def test_plan_md_obligation_lines_are_markdownlint_clean() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input", origin="llm")
    assert_markdownlint_clean(render_plan(p, None))
