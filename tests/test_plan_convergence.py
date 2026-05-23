"""Tests for non-blocking convergence warnings — parallel/TDD fitness (#13, t3).

These tests cover:
  - warning_missing_acceptance: confirmed tasks with zero acceptance criteria
  - warning_over_serialized: all active tasks form a purely serial chain (every wave = 1 task,
    3+ active tasks)
  - within_wave_independence: no task in a wave depends on another task in the same wave
    (property test on the existing dependency_waves function)
"""

from __future__ import annotations

from devague.plan import CoverageTarget, Plan, Task, dependency_waves
from devague.plan_convergence import evaluate

# ── helpers ───────────────────────────────────────────────────────────────────


def _plan_with_tasks(
    specs: list[tuple[str, list[str], str, list[str]]],
) -> Plan:
    """Build a Plan from ``(summary, deps, status, acceptance_criteria)`` rows.

    ids are t1.. in stored order; targets are auto-created to keep the plan
    otherwise convergence-clean (each confirmed task covers its own target).
    """
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    for i, (summary, deps, status, acceptance) in enumerate(specs, start=1):
        t = Task(
            id=f"t{i}",
            summary=summary,
            status=status,
            deps=list(deps),
            acceptance_criteria=list(acceptance),
        )
        p.tasks.append(t)
        if status == "confirmed":
            tgt = CoverageTarget(id=f"c{i}", kind="requirement", text=summary)
            p.targets.append(tgt)
            t.covers.append(f"c{i}")
    return p


def _converging() -> Plan:
    """Minimal plan that is fully converged: one confirmed task, one target, criteria."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [CoverageTarget(id="c1", kind="announcement", text="shipped")]
    t = p.add_task("do the thing")  # confirmed
    p.add_acceptance(t, "it works")
    p.add_cover(t, "c1")
    return p


# ── warning: missing acceptance criteria ──────────────────────────────────────


def test_no_warning_when_confirmed_task_has_acceptance() -> None:
    """A converged plan with acceptance criteria on every confirmed task has no warnings."""
    res = evaluate(_converging())
    assert res.ready is True
    assert res.warnings == []


def test_warning_when_confirmed_task_has_no_acceptance_criteria() -> None:
    """A confirmed task with zero acceptance criteria emits a non-blocking warning.

    The warning does NOT flip ready_for_plan or appear in blockers — it is purely
    advisory, reminding the operator that TDD fitness requires crisp acceptance tests.
    """
    p = _plan_with_tasks(
        [
            ("implement core", [], "confirmed", []),  # no acceptance — triggers warning
        ]
    )
    res = evaluate(p)
    # Must be a warning, not a blocker.
    assert any(
        "t1" in w and "acceptance" in w for w in res.warnings
    ), f"expected acceptance-criteria warning in warnings, got: {res.warnings}"
    # ready_for_plan is false here because confirmed-no-acceptance IS also a blocker
    # (existing gate); the warning is ADDITIONAL advisory output, not a replacement.
    # The key invariant: warnings never flip a converging plan to non-converging.


def test_warning_acceptance_does_not_affect_ready_for_plan() -> None:
    """A confirmed task's missing acceptance criteria warning must NOT flip ready_for_plan.

    Construct a plan where the only issue is missing acceptance on a confirmed task.
    ready_for_plan is already False due to the existing blocker; the warning fires too
    but does not independently affect the gate.
    """
    p = _plan_with_tasks([("task", [], "confirmed", [])])
    res = evaluate(p)
    # blocker exists (existing gate)
    assert any("acceptance" in b for b in res.blockers)
    # warning also fires
    assert any("acceptance" in w for w in res.warnings)
    # warnings list is separate from blockers — no overlap in list objects
    for w in res.warnings:
        assert w not in res.blockers


def test_warning_does_not_fire_for_proposed_task_without_acceptance() -> None:
    """Proposed tasks without acceptance criteria do NOT trigger the acceptance warning.

    Proposed tasks are not yet confirmed; they become a blocker (proposed task gate)
    but the TDD-fitness acceptance warning is limited to confirmed tasks only.
    """
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.add_task("speculative", origin="llm")  # proposed, no acceptance
    res = evaluate(p)
    # The warning must NOT mention t1 for the acceptance criterion reason.
    acceptance_warnings = [w for w in res.warnings if "acceptance" in w and "t1" in w]
    assert (
        acceptance_warnings == []
    ), f"acceptance warning should not fire for proposed tasks: {acceptance_warnings}"


def test_warning_does_not_fire_for_rejected_task_without_acceptance() -> None:
    """Rejected tasks without acceptance criteria do NOT trigger the acceptance warning."""
    p = _converging()
    t = p.add_task("dropped")
    p.set_status(t.id, "rejected")
    # t2 is rejected and has no acceptance criteria — no warning
    res = evaluate(p)
    acceptance_warnings = [w for w in res.warnings if "t2" in w and "acceptance" in w]
    assert (
        acceptance_warnings == []
    ), f"acceptance warning should not fire for rejected tasks: {acceptance_warnings}"


def test_converging_plan_has_zero_warnings() -> None:
    """A fully converged, well-parallelized plan emits zero warnings."""
    # Two independent confirmed tasks (parallel, not serial) both with acceptance criteria.
    p = _plan_with_tasks(
        [
            ("task A", [], "confirmed", ["works"]),
            ("task B", [], "confirmed", ["passes"]),
        ]
    )
    res = evaluate(p)
    assert res.ready is True
    assert res.warnings == []


# ── warning: over-serialized graph ────────────────────────────────────────────


def test_no_over_serialization_warning_for_parallel_tasks() -> None:
    """A plan where tasks can run in parallel should not trigger the serialization warning."""
    # t1 (root), t2 and t3 both depend only on t1 — wave 0: [t1], wave 1: [t2, t3]
    p = _plan_with_tasks(
        [
            ("root", [], "confirmed", ["root done"]),
            ("branch A", ["t1"], "confirmed", ["A done"]),
            ("branch B", ["t1"], "confirmed", ["B done"]),
        ]
    )
    res = evaluate(p)
    serial_warnings = [w for w in res.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert (
        serial_warnings == []
    ), f"parallel plan should have no serialization warning: {serial_warnings}"


def test_over_serialization_warning_for_fully_linear_chain() -> None:
    """A purely serial chain of 3+ active tasks emits a non-blocking warning.

    Heuristic: every wave has exactly one task AND there are >= 3 active (non-rejected)
    confirmed tasks. This reliably flags a plan that could have been parallelized but
    was expressed as t1 -> t2 -> t3 -> ... with no fan-out.
    """
    # t1 -> t2 -> t3: three waves of size 1
    p = _plan_with_tasks(
        [
            ("step 1", [], "confirmed", ["s1 ok"]),
            ("step 2", ["t1"], "confirmed", ["s2 ok"]),
            ("step 3", ["t2"], "confirmed", ["s3 ok"]),
        ]
    )
    res = evaluate(p)
    serial_warnings = [w for w in res.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert (
        serial_warnings
    ), f"expected over-serialization warning for linear chain, got warnings: {res.warnings}"


def test_over_serialization_warning_does_not_affect_ready_for_plan() -> None:
    """The over-serialization warning must NOT flip ready_for_plan on an otherwise converging plan.

    A plan with a linear chain of 3 fully-covered, accepted tasks is still ready_for_plan;
    the warning is purely advisory.
    """
    p = _plan_with_tasks(
        [
            ("step 1", [], "confirmed", ["s1 ok"]),
            ("step 2", ["t1"], "confirmed", ["s2 ok"]),
            ("step 3", ["t2"], "confirmed", ["s3 ok"]),
        ]
    )
    res = evaluate(p)
    # The plan converges (all targets covered, all tasks have criteria, no blockers)
    assert res.ready is True, f"expected convergence; blockers: {res.blockers}"
    # But we still get the warning
    serial_warnings = [w for w in res.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert serial_warnings, "expected warning even on converged plan"


def test_no_over_serialization_warning_for_one_or_two_tasks() -> None:
    """A single task or two-task chain does NOT trigger the over-serialization warning.

    One or two tasks being serial is not actionably problematic — the heuristic only
    fires at 3+ active tasks (all of which form a single-task-per-wave chain).
    """
    # Single task: no serial warning
    p_one = _plan_with_tasks([("only", [], "confirmed", ["ok"])])
    res_one = evaluate(p_one)
    serial_one = [w for w in res_one.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert serial_one == [], f"single task should not warn: {serial_one}"

    # Two-task chain: t1 -> t2
    p_two = _plan_with_tasks(
        [
            ("step 1", [], "confirmed", ["ok"]),
            ("step 2", ["t1"], "confirmed", ["ok"]),
        ]
    )
    res_two = evaluate(p_two)
    serial_two = [w for w in res_two.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert serial_two == [], f"two-task chain should not warn: {serial_two}"


def test_over_serialization_excludes_rejected_tasks() -> None:
    """Rejected tasks are excluded when counting active tasks for the serial heuristic.

    A plan with 3 tasks where one is rejected results in 2 active tasks — below the
    3-task threshold, so no over-serialization warning.
    """
    # t1 -> t2 -> t3 (t2 rejected) => active: t1, t3; but t3 dep on t2 is a blocker,
    # so use a simpler scenario: 3 tasks total but 1 rejected, 2 active, no chain.
    p = _plan_with_tasks(
        [
            ("step 1", [], "confirmed", ["ok"]),
            ("dropped", [], "confirmed", ["ok"]),
            ("step 3", ["t1"], "confirmed", ["ok"]),
        ]
    )
    p.set_status("t2", "rejected")
    # active tasks: t1, t3 — t1 feeds t3, that's a 2-task chain, no wave warning
    res = evaluate(p)
    serial_warnings = [w for w in res.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert (
        serial_warnings == []
    ), f"2 active tasks (1 rejected) should not trigger serial warning: {serial_warnings}"


def test_over_serialization_only_counts_confirmed_tasks() -> None:
    """Proposed tasks are excluded when counting active confirmed tasks for the heuristic."""
    # 3 tasks: t1 confirmed, t2 proposed (no acceptance, llm), t3 confirmed depending on t1
    # => only 2 confirmed active tasks in the chain
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [
        CoverageTarget(id="c1", kind="requirement", text="req 1"),
        CoverageTarget(id="c3", kind="requirement", text="req 3"),
    ]
    t1 = p.add_task("step 1")  # confirmed
    p.add_acceptance(t1, "ok")
    p.add_cover(t1, "c1")
    p.add_task("speculative", origin="llm")  # proposed, t2
    t3 = p.add_task("step 3")  # confirmed
    t3.deps = ["t1"]
    p.add_acceptance(t3, "ok")
    p.add_cover(t3, "c3")
    res = evaluate(p)
    # Only 2 confirmed active tasks — no serial warning expected
    serial_warnings = [w for w in res.warnings if "serial" in w.lower() or "parallel" in w.lower()]
    assert (
        serial_warnings == []
    ), f"2 confirmed active tasks should not trigger serial warning: {serial_warnings}"


# ── within-wave independence (property assertion) ─────────────────────────────


def test_within_wave_tasks_have_no_inter_task_dependency() -> None:
    """Tasks in the same wave must have no dependency on another task in the same wave.

    This is an invariant of the dependency_waves algorithm: by definition, a task enters
    wave N only when all its deps are in waves 0..N-1. Therefore no task in wave N can
    depend on another task also in wave N.
    """
    # Fan-out + join: wave 0=[t1], wave 1=[t2,t3,t4], wave 2=[t5]
    specs = [
        ("root", [], "confirmed"),
        ("branch A", ["t1"], "confirmed"),
        ("branch B", ["t1"], "confirmed"),
        ("branch C", ["t1"], "confirmed"),
        ("join", ["t2", "t3", "t4"], "confirmed"),
    ]
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    for summary, deps, status in specs:
        t = p.add_task(summary)
        t.deps = list(deps)
        t.status = status

    waves = dependency_waves(p.tasks)
    assert len(waves) == 3, f"expected 3 waves, got: {waves}"

    for wave in waves:
        wave_set = set(wave)
        for tid in wave:
            task = p.find_task(tid)
            assert task is not None
            inter_deps = [d for d in task.deps if d in wave_set]
            assert (
                inter_deps == []
            ), f"task {tid} in wave {wave} depends on {inter_deps} which are in the same wave"


def test_within_wave_independence_linear_chain() -> None:
    """Each task in a linear chain is its own wave: trivially no inter-wave violations."""
    specs = [
        ("a", [], "confirmed"),
        ("b", ["t1"], "confirmed"),
        ("c", ["t2"], "confirmed"),
    ]
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    for summary, deps, status in specs:
        t = p.add_task(summary)
        t.deps = list(deps)
        t.status = status

    waves = dependency_waves(p.tasks)
    assert waves == [["t1"], ["t2"], ["t3"]]

    for wave in waves:
        wave_set = set(wave)
        for tid in wave:
            task = p.find_task(tid)
            inter_deps = [d for d in task.deps if d in wave_set]
            assert inter_deps == []


def test_within_wave_independence_fully_parallel_plan() -> None:
    """All independent tasks share one wave: none depends on any other in the same wave."""
    specs = [
        ("a", [], "confirmed"),
        ("b", [], "confirmed"),
        ("c", [], "confirmed"),
        ("d", [], "confirmed"),
    ]
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    for summary, deps, status in specs:
        t = p.add_task(summary)
        t.deps = list(deps)
        t.status = status

    waves = dependency_waves(p.tasks)
    assert waves == [["t1", "t2", "t3", "t4"]]

    for wave in waves:
        wave_set = set(wave)
        for tid in wave:
            task = p.find_task(tid)
            inter_deps = [d for d in task.deps if d in wave_set]
            assert inter_deps == []


# ── combined: warnings + blockers coexist cleanly ─────────────────────────────


def test_warnings_and_blockers_are_independent_lists() -> None:
    """Warnings and blockers are never the same list object and share no items."""
    p = _plan_with_tasks([("task", [], "confirmed", [])])  # no acceptance: both blocker + warning
    res = evaluate(p)
    assert res.warnings is not res.blockers
    for w in res.warnings:
        assert w not in res.blockers, f"warning {w!r} leaked into blockers"


def test_ready_for_plan_unchanged_by_warnings_only() -> None:
    """A plan that would converge without warnings still converges WITH warnings.

    Build a 3-task converged linear chain — it will have acceptance criteria (convergence)
    but still emit a serial/parallelism warning. ready must remain True.
    """
    p = _plan_with_tasks(
        [
            ("step 1", [], "confirmed", ["s1 ok"]),
            ("step 2", ["t1"], "confirmed", ["s2 ok"]),
            ("step 3", ["t2"], "confirmed", ["s3 ok"]),
        ]
    )
    res = evaluate(p)
    assert res.ready is True
    # warnings present (over-serialized)
    assert any("serial" in w.lower() or "parallel" in w.lower() for w in res.warnings)
    # blockers empty
    assert res.blockers == []
