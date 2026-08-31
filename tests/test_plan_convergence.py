"""Tests for non-blocking convergence warnings — parallel/TDD fitness (#13, t3).

These tests cover:
  - warning_missing_acceptance: confirmed tasks with zero acceptance criteria
  - warning_over_serialized: all active tasks form a purely serial chain (every wave = 1 task,
    3+ active tasks)
  - within_wave_independence: no task in a wave depends on another task in the same wave
    (property test on the existing dependency_waves function)
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from devague.frame import LAPSE_CODES, Frame
from devague.plan import CoverageTarget, Plan, Task, dependency_waves, targets_from_frame
from devague.plan_convergence import evaluate, suggest_move

# ── helpers ───────────────────────────────────────────────────────────────────


def _plan_with_tasks(
    specs: list[tuple[str, list[str], str, list[str]]],
) -> Plan:
    """Build a Plan from ``(summary, deps, status, acceptance_criteria)`` rows.

    ids are t1.. in stored order; targets are auto-created to keep the plan
    otherwise convergence-clean (each confirmed task covers its own target).
    Confirmed tasks automatically get a default instruction to avoid TDD warnings.
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
        if status == "confirmed":
            t.instruction = f"implement {summary}"
        p.tasks.append(t)
        if status == "confirmed":
            tgt = CoverageTarget(id=f"c{i}", kind="requirement", text=summary)
            p.targets.append(tgt)
            t.covers.append(f"c{i}")
    return p


def _converging() -> Plan:
    """Minimal plan that is fully converged: one task, target, criteria, instruction."""
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.targets = [CoverageTarget(id="c1", kind="announcement", text="shipped")]
    t = p.add_task("do the thing")  # confirmed
    t.instruction = "implement the feature"
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


# ── blocking risk resolution (resolve-parked-vagueness t4, mirrors t3) ─────────


def test_unresolved_blocking_risk_blocks_convergence() -> None:
    """Baseline: an unresolved unknown_blocking risk still blocks convergence."""
    p = _converging()
    p.add_risk("scope unclear", "unknown_blocking")
    res = evaluate(p)
    assert res.ready is False
    assert any("blocking risk r1" in b for b in res.blockers)


def test_resolved_blocking_risk_no_longer_blocks_convergence() -> None:
    """A resolved unknown_blocking risk must not block plan convergence (t4 AC1)."""
    p = _converging()
    r = p.add_risk("scope unclear", "unknown_blocking")
    p.resolve_risk(r.id, "decided: ship option B")
    res = evaluate(p)
    assert res.ready is True, f"expected convergence; blockers: {res.blockers}"
    assert not any("blocking risk" in b for b in res.blockers)


def test_resolved_blocking_risk_does_not_appear_in_required_next_moves() -> None:
    """A resolved risk generates no follow-up hint since it is no longer a blocker."""
    p = _converging()
    r = p.add_risk("scope unclear", "unknown_blocking")
    p.resolve_risk(r.id, "decided: ship option B")
    res = evaluate(p)
    assert not any("risk" in m for m in res.required_next_moves)


def test_blocking_risk_hint_names_executable_resolve_syntax() -> None:
    """The blocking-risk hint names the executable ``plan risk --resolve``
    syntax with the actual risk id interpolated (t4 AC2), mirroring t3's
    frame-side ``park --resolve v1 --decision "<the decision>"`` hint shape.
    """
    hint = suggest_move("blocking risk r1 unresolved")
    assert 'devague plan risk --resolve r1 --decision "<the decision>"' in hint


def test_blocking_risk_hint_end_to_end_via_evaluate() -> None:
    """The same executable-syntax hint surfaces through evaluate()'s required_next_moves."""
    p = _converging()
    p.add_risk("scope unclear", "unknown_blocking")
    res = evaluate(p)
    assert any("plan risk --resolve r1 --decision" in m for m in res.required_next_moves)


def test_resolved_risk_excluded_from_parked_items() -> None:
    """Plan-side _parked_items excludes resolved risks (t4 AC3)."""
    p = _converging()
    r = p.add_risk("a non-blocking risk", "unknown_nonblocking")
    res = evaluate(p)
    assert any("a non-blocking risk" in item for item in res.parked_items)
    p.resolve_risk(r.id, "decided: not an issue")
    res2 = evaluate(p)
    assert not any("a non-blocking risk" in item for item in res2.parked_items)


# ── per-target deferral (issue #85, t9) ───────────────────────────────────────


def test_deferred_target_does_not_block_convergence() -> None:
    """Baseline: an uncovered, deferred target is not a coverage blocker."""
    p = _converging()  # one task covering c1
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    p.defer_target("c47", "Milestone 3: worktree mechanics")
    res = evaluate(p)
    assert res.ready is True, f"expected convergence; blockers: {res.blockers}"
    assert not any("c47" in b for b in res.blockers)


def test_uncovered_undeferred_target_still_blocks() -> None:
    """A target that is neither covered nor deferred remains a real blocker —
    deferral must be an explicit decision, not a side effect of merely existing."""
    p = _converging()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    res = evaluate(p)
    assert res.ready is False
    assert any("coverage target c47" in b and "has no confirmed task" in b for b in res.blockers)


def test_deferred_target_appears_in_parked_items_distinctly() -> None:
    """A deferred target surfaces in parked_items labeled distinctly from a plain
    unresolved risk, so a reviewer can tell 'deliberately deferred' apart from
    'not yet covered' or 'an open risk' at a glance."""
    p = _converging()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    p.defer_target("c47", "Milestone 3: worktree mechanics")
    res = evaluate(p)
    matches = [item for item in res.parked_items if "c47" in item]
    assert matches, f"expected a parked item naming c47, got: {res.parked_items}"
    assert "deferred" in matches[0]
    assert "Milestone 3: worktree mechanics" in matches[0]


def test_deferred_target_absent_from_required_next_moves() -> None:
    """A deferred target generates no follow-up hint — it is not a blocker."""
    p = _converging()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    p.defer_target("c47", "Milestone 3")
    res = evaluate(p)
    assert not any("c47" in m for m in res.required_next_moves)


def test_undeferred_target_blocks_again() -> None:
    """Reversing a deferral (``undefer_target``) restores the target as a real
    blocker — deferral is not a permanent write-off once undone."""
    p = _converging()
    p.targets.append(CoverageTarget(id="c47", kind="requirement", text="worktree concurrency"))
    p.defer_target("c47", "Milestone 3")
    p.undefer_target("c47")
    res = evaluate(p)
    assert res.ready is False
    assert any("coverage target c47" in b for b in res.blockers)


def test_shell_cli_shape_90_covered_12_deferred_converges() -> None:
    """The exact repro shape from issue #85's comment thread: a plan confirmed
    and complete — 19 tasks / 9 waves in the real repro, simplified here to one
    covering task per covered target — with 90 of 102 coverage targets covered
    and the remaining 12 deliberately deferred to a later milestone. It must
    converge cleanly, with zero coverage blockers and every deferred target
    named in parked_items.
    """
    p = Plan(slug="milestone-scoped", title="Milestone-scoped plan", frame_slug="milestone-scoped")
    covered_ids = [f"c{i}" for i in range(1, 91)]
    deferred_ids = [f"c{i}" for i in range(91, 103)]
    for tid in covered_ids:
        p.targets.append(CoverageTarget(id=tid, kind="requirement", text=f"target {tid}"))
    for tid in deferred_ids:
        p.targets.append(CoverageTarget(id=tid, kind="requirement", text=f"target {tid}"))
    assert len(p.targets) == 102

    t = p.add_task("deliver the in-scope milestones")
    t.instruction = "implement every in-scope target"
    p.add_acceptance(t, "all 90 in-scope targets pass their own acceptance checks")
    for tid in covered_ids:
        p.add_cover(t, tid)

    for tid in deferred_ids:
        p.defer_target(tid, "belongs to a later milestone plan")

    res = evaluate(p)
    assert res.ready is True, f"expected convergence; blockers: {res.blockers}"
    assert res.blockers == []
    deferred_parked = [item for item in res.parked_items if "deferred" in item]
    assert len(deferred_parked) == 12
    for tid in deferred_ids:
        assert any(tid in item for item in deferred_parked)


# --- Reasoning Degradation Ledger (issue #97, t4): the plan gate is lapse-inert
#
# Frame.lapses records reasoning degradation; it must never GATE — on either
# side. Plan itself carries no lapses field at all, and plan_convergence.evaluate
# never sees the source frame directly (only `plan` + optional `targets`), so the
# property under test here is really about `targets_from_frame`: filing a lapse
# on the source frame — in any status — must not perturb the coverage targets a
# plan derives from it, and therefore must not perturb the plan gate's output.


def _frame_with_confirmed_requirement() -> Frame:
    f = Frame(slug="src", title="Source frame")
    f.add_claim("requirement", "must round-trip", origin="user")  # confirmed -> c1
    return f


def _plan_from_targets(targets: list[CoverageTarget], frame_slug: str) -> Plan:
    """A plan that covers every target with acceptance + instruction on every
    confirmed task — the plan-side twin of test_convergence's ``_full_frame``:
    a plan that converges cleanly given ``targets``."""
    p = Plan(slug="demo", title="Demo", frame_slug=frame_slug)
    p.targets = list(targets)
    for tg in targets:
        t = p.add_task(f"deliver {tg.id}")
        t.instruction = f"implement {tg.id}"
        p.add_acceptance(t, f"{tg.id} verified")
        p.add_cover(t, tg.id)
    return p


def _serialize(res) -> str:
    """Canonical string form so "converges identically" is checked literally,
    not just via dataclass ``==`` (which these tests also assert separately)."""
    return json.dumps(dataclasses.asdict(res), sort_keys=True)


_LAPSE_SENTINEL_WHAT = "SENTINEL-PLAN-LAPSE-WHAT-7c1e9b02"
_LAPSE_SENTINEL_SKIPPED_CHECK = "SENTINEL-PLAN-LAPSE-SKIPPED-CHECK-3fa88d17"


def _file_lapse(f: Frame, origin: str, final_status: str):
    """File one distinctively-worded lapse on ``f``, driving it to
    ``final_status`` — mirrors test_convergence.py's helper of the same name."""
    lapse = f.add_lapse(
        LAPSE_CODES[0],
        _LAPSE_SENTINEL_WHAT,
        skipped_check=_LAPSE_SENTINEL_SKIPPED_CHECK,
        refs=["c1"],
        origin=origin,
    )
    if final_status == "rejected":
        f.set_lapse_status(lapse.id, "rejected")
    assert lapse.status == final_status
    return lapse


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_plan_converges_identically_whether_source_frame_carries_a_lapse_or_not(
    origin, final_status
) -> None:
    """A plan seeded from a lapse-free frame and a plan seeded from an
    otherwise-identical frame that ALSO carries a filed lapse (in any status)
    must converge byte-identically — the ledger must never leak into
    coverage-target derivation or the plan gate."""
    clean_frame = _frame_with_confirmed_requirement()
    clean_targets = targets_from_frame(clean_frame)
    clean_plan = _plan_from_targets(clean_targets, clean_frame.slug)
    baseline = evaluate(clean_plan)
    baseline_str = _serialize(baseline)

    lapsy_frame = _frame_with_confirmed_requirement()
    _file_lapse(lapsy_frame, origin, final_status)
    lapsy_targets = targets_from_frame(lapsy_frame)
    lapsy_plan = _plan_from_targets(lapsy_targets, lapsy_frame.slug)

    # Sanity: filing the lapse changed nothing about the derived targets either.
    assert lapsy_targets == clean_targets

    after = evaluate(lapsy_plan)
    assert after == baseline
    assert _serialize(after) == baseline_str


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_plan_convergence_output_stays_lapse_free_on_converged_plan(origin, final_status) -> None:
    """AC2 on the plan side: the plan gate's blockers/warnings/parked_items/
    required_next_moves never name a lapse id, code, or filed text, in any
    lapse status — for a converged plan derived from a lapse-carrying frame."""
    frame = _frame_with_confirmed_requirement()
    lapse = _file_lapse(frame, origin, final_status)
    targets = targets_from_frame(frame)
    plan = _plan_from_targets(targets, frame.slug)

    res = evaluate(plan)
    assert res.ready is True  # sanity: this plan genuinely converges
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_plan_convergence_output_stays_lapse_free_on_unconverged_plan(origin, final_status) -> None:
    """AC2, the other half: an INCOMPLETE plan (real coverage blockers present,
    since nothing covers the target) derived from a lapse-carrying frame must
    still keep every blocker/warning/parked_item/required_next_move lapse-free."""
    frame = _frame_with_confirmed_requirement()
    lapse = _file_lapse(frame, origin, final_status)
    targets = targets_from_frame(frame)
    plan = Plan(slug="demo", title="Demo", frame_slug=frame.slug)
    plan.targets = targets  # uncovered — genuinely unconverged, no tasks at all

    res = evaluate(plan)
    assert res.ready is False  # sanity: this plan genuinely does not converge
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


# --- Unmet-obligation warnings (bvts t7): warning-only, and lapse-free --------
#
# The plan-side twin of test_convergence.py's section of the same name: a
# criterion obligation with no approved evidence warns and does nothing else,
# and no warning text is ever derived from the source frame's lapse ledger.


@pytest.mark.parametrize(
    "origin,final_status",
    [
        ("llm", "proposed"),
        ("user", "approved"),
        ("user", "rejected"),
    ],
)
def test_plan_unmet_obligation_warning_never_gates(origin, final_status) -> None:
    """``ready_for_plan``, blockers, parked_items and required_next_moves are
    identical to the obligation-free baseline; only ``warnings`` grows."""
    frame = _frame_with_confirmed_requirement()
    targets = targets_from_frame(frame)
    baseline = evaluate(_plan_from_targets(targets, frame.slug))

    plan = _plan_from_targets(targets, frame.slug)
    ob = plan.add_obligation("t1", 1, "store round-trip", "the ledger reloads", origin=origin)
    if final_status == "rejected":
        plan.set_obligation_status(ob.id, "rejected")
    res = evaluate(plan, met_obligations=set())

    assert res.ready is baseline.ready is True
    assert res.blockers == baseline.blockers
    assert res.parked_items == baseline.parked_items
    assert res.required_next_moves == baseline.required_next_moves
    expected = 0 if final_status == "rejected" else 1
    assert len([w for w in res.warnings if ob.id in w]) == expected


def test_plan_obligation_warnings_never_derive_from_lapses() -> None:
    """With a lapse on the source frame AND an unmet criterion obligation on
    the plan, the obligation warning appears and nothing names the lapse."""
    frame = _frame_with_confirmed_requirement()
    lapse = _file_lapse(frame, "user", "approved")
    plan = _plan_from_targets(targets_from_frame(frame), frame.slug)
    ob = plan.add_obligation("t1", 1, "store round-trip", "the ledger reloads")

    res = evaluate(plan, met_obligations=set())
    haystack = " ".join(res.blockers + res.warnings + res.parked_items + res.required_next_moves)
    assert any(ob.id in w and "untested" in w for w in res.warnings)
    assert lapse.id not in haystack
    assert lapse.code not in haystack
    assert _LAPSE_SENTINEL_WHAT not in haystack
    assert _LAPSE_SENTINEL_SKIPPED_CHECK not in haystack


def test_plan_obligation_warning_clears_when_evidence_is_met() -> None:
    frame = _frame_with_confirmed_requirement()
    plan = _plan_from_targets(targets_from_frame(frame), frame.slug)
    ob = plan.add_obligation("t1", 1, "store round-trip", "the ledger reloads")
    baseline = evaluate(_plan_from_targets(targets_from_frame(frame), frame.slug))
    assert evaluate(plan, met_obligations={ob.id}) == baseline
