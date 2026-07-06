"""Tests for the instruction warning in plan convergence (#53 t8).

These tests cover:
  - warning_missing_instruction: confirmed tasks without an instruction
  - interaction with existing convergence state
"""

from __future__ import annotations

from devague.plan import CoverageTarget, Plan
from devague.plan_convergence import evaluate

# ── helpers ───────────────────────────────────────────────────────────────────


def _converging_with_instruction() -> Plan:
    """Minimal plan that is fully converged: one confirmed task with instruction."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [CoverageTarget(id="c1", kind="announcement", text="shipped")]
    t = p.add_task("do the thing")  # confirmed
    t.instruction = "implement feature X"  # has instruction
    p.add_acceptance(t, "it works")
    p.add_cover(t, "c1")
    return p


def _converging_without_instruction() -> Plan:
    """Minimal plan that is fully converged except for missing instruction on task."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [CoverageTarget(id="c1", kind="announcement", text="shipped")]
    t = p.add_task("do the thing")  # confirmed
    # instruction defaults to "" — no instruction
    p.add_acceptance(t, "it works")
    p.add_cover(t, "c1")
    return p


# ── warning: missing instruction ──────────────────────────────────────────────


def test_no_warning_when_confirmed_task_has_instruction() -> None:
    """A converged plan with instruction on every confirmed task has no instruction warnings."""
    res = evaluate(_converging_with_instruction())
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert (
        instruction_warnings == []
    ), f"should have no instruction warnings, got: {instruction_warnings}"


def test_warning_when_confirmed_task_has_no_instruction() -> None:
    """A confirmed task with empty instruction emits a non-blocking warning.

    The warning does NOT flip ready_for_plan or appear in blockers — it is purely
    advisory.
    """
    res = evaluate(_converging_without_instruction())
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert instruction_warnings, f"expected instruction warning, got: {res.warnings}"
    # Verify the warning references the task id and suggests the fix move
    assert any(
        "t1" in w for w in instruction_warnings
    ), f"warning should mention t1: {instruction_warnings}"
    assert any(
        "instruct" in w.lower() for w in instruction_warnings
    ), f"warning should suggest instruct move: {instruction_warnings}"


def test_instruction_warning_does_not_affect_ready_for_plan() -> None:
    """A confirmed task's missing instruction warning must NOT flip ready_for_plan.

    A converged plan (all targets covered, all tasks have acceptance criteria)
    that is missing an instruction should still converge; the warning fires but
    does not independently affect ready_for_plan.
    """
    p = _converging_without_instruction()
    res = evaluate(p)
    # The plan converges (all targets covered, all tasks have criteria)
    assert res.ready is True, f"expected convergence; blockers: {res.blockers}"
    # But we still get the warning
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert instruction_warnings, "expected instruction warning even on converged plan"


def test_no_warning_for_proposed_task_without_instruction() -> None:
    """Proposed tasks without instruction do NOT trigger the instruction warning.

    Proposed tasks are not yet confirmed; the instruction warning is limited to
    confirmed tasks only.
    """
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.add_task("speculative", origin="llm")  # proposed, no instruction
    res = evaluate(p)
    # The warning must NOT mention t1 for the instruction reason.
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower() and "t1" in w]
    assert (
        instruction_warnings == []
    ), f"instruction warning should not fire for proposed tasks: {instruction_warnings}"


def test_no_warning_for_rejected_task_without_instruction() -> None:
    """Rejected tasks without instruction do NOT trigger the instruction warning."""
    p = _converging_with_instruction()
    t = p.add_task("dropped")
    p.set_status(t.id, "rejected")
    # t2 is rejected and has no instruction — no warning
    res = evaluate(p)
    instruction_warnings = [w for w in res.warnings if "t2" in w and "instruction" in w.lower()]
    assert (
        instruction_warnings == []
    ), f"instruction warning should not fire for rejected tasks: {instruction_warnings}"


def test_multiple_confirmed_tasks_missing_instruction() -> None:
    """Multiple confirmed tasks without instruction all get warnings."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [
        CoverageTarget(id="c1", kind="requirement", text="req 1"),
        CoverageTarget(id="c2", kind="requirement", text="req 2"),
    ]
    t1 = p.add_task("task 1")  # no instruction
    p.add_acceptance(t1, "ok")
    p.add_cover(t1, "c1")
    t2 = p.add_task("task 2")  # no instruction
    p.add_acceptance(t2, "ok")
    p.add_cover(t2, "c2")
    res = evaluate(p)
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert (
        len(instruction_warnings) == 2
    ), f"expected 2 instruction warnings, got: {instruction_warnings}"
    assert any("t1" in w for w in instruction_warnings)
    assert any("t2" in w for w in instruction_warnings)


def test_mixed_tasks_with_and_without_instruction() -> None:
    """Some tasks have instructions, some don't — only the missing ones warn."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [
        CoverageTarget(id="c1", kind="requirement", text="req 1"),
        CoverageTarget(id="c2", kind="requirement", text="req 2"),
    ]
    t1 = p.add_task("task 1")
    t1.instruction = "do this"  # has instruction
    p.add_acceptance(t1, "ok")
    p.add_cover(t1, "c1")
    t2 = p.add_task("task 2")
    # no instruction
    p.add_acceptance(t2, "ok")
    p.add_cover(t2, "c2")
    res = evaluate(p)
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert (
        len(instruction_warnings) == 1
    ), f"expected 1 instruction warning, got: {instruction_warnings}"
    assert any("t2" in w for w in instruction_warnings)
    assert not any("t1" in w for w in instruction_warnings)


def test_converging_plan_with_all_instructions_has_no_instruction_warnings() -> None:
    """All-instruction converged plan has no instruction warnings."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [
        CoverageTarget(id="c1", kind="requirement", text="req 1"),
        CoverageTarget(id="c2", kind="requirement", text="req 2"),
    ]
    t1 = p.add_task("task 1")
    t1.instruction = "implement feature A"
    p.add_acceptance(t1, "works")
    p.add_cover(t1, "c1")
    t2 = p.add_task("task 2")
    t2.instruction = "implement feature B"
    p.add_acceptance(t2, "works")
    p.add_cover(t2, "c2")
    res = evaluate(p)
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert (
        instruction_warnings == []
    ), f"should have no instruction warnings, got: {instruction_warnings}"
    assert res.ready is True


def test_instruction_warning_includes_suggested_fix() -> None:
    """The instruction warning includes the exact suggested fix move."""
    res = evaluate(_converging_without_instruction())
    instruction_warnings = [w for w in res.warnings if "instruction" in w.lower()]
    assert instruction_warnings, "should have instruction warning"
    # The warning should suggest the devague plan instruct move with backticks
    assert any(
        "`devague plan instruct" in w for w in instruction_warnings
    ), f"warning should include exact fix move with backticks: {instruction_warnings}"
