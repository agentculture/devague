"""The plan convergence gate: is a plan solid enough to export a buildable plan?

The peer of :mod:`devague.convergence`. A plan converges when every coverage target
is either covered by a confirmed task or deliberately deferred (``plan defer``,
issue #85), every confirmed task carries acceptance criteria, the dependency graph
is sound (no dangling refs, no cycles), nothing is left proposed, and no blocking
risk remains. Reuses :class:`devague.convergence.ConvergenceResult` so both
engines report the same structured ``{ready, blockers, warnings, parked_items,
required_next_moves}`` shape (the CLI serializes ``ready`` as ``ready_for_plan``).

Like its frame-side peer it also emits **warning-only** signals that never move
``ready_for_plan``: the three TDD-fitness heuristics
(:func:`_tdd_fitness_warnings`) and, since bvts t7, one unmet-obligation
warning per criterion obligation with no approved evidence
(:func:`_unmet_obligation_warnings` — the plan-side twin of
:mod:`devague.convergence`'s S3). No warning here is ever derived from
``Frame.lapses``: the Reasoning Degradation Ledger stays gate-inert *and*
warning-inert on both engines (issue #97), and ``Plan`` carries no lapses at
all.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from devague.convergence import ConvergenceResult
from devague.plan import CoverageTarget, Plan, Task, dependency_waves


def _missing_tasks(plan: Plan) -> list[str]:
    if not plan.tasks:
        return ["no tasks yet (add at least one with 'plan task')"]
    return []


def _missing_coverage(plan: Plan, targets: list[CoverageTarget]) -> list[str]:
    """Targets with no confirmed covering task — excluding deliberately
    deferred ones (issue #85).

    A deferred target is a documented, honest decision (``plan defer``) that a
    milestone-scoped plan will not cover it here; it must not block convergence
    the way a target nobody has decided about yet does. It still shows up
    elsewhere — as a tracked item in :func:`_parked_items` and in the exported
    plan's "Deferred targets" section — so the exclusion stays visible instead
    of silently implied by the absence of a blocker.
    """
    covered = {tid for t in plan.tasks if t.status == "confirmed" for tid in t.covers}
    return [
        f"coverage target {tg.id} ({tg.kind}) has no confirmed task"
        for tg in targets
        if tg.id not in covered and not tg.deferred
    ]


def _missing_acceptance(plan: Plan) -> list[str]:
    return [
        f"task {t.id} has no acceptance criteria"
        for t in plan.tasks
        if t.status == "confirmed" and not t.acceptance_criteria
    ]


def _missing_resolution(plan: Plan) -> list[str]:
    return [
        f"task {t.id} still proposed (confirm or reject it)"
        for t in plan.tasks
        if t.status == "proposed"
    ]


_WHITE, _GRAY, _BLACK = 0, 1, 2


def _walk_from(root: str, deps: dict[str, list[str]], color: dict[str, int]) -> Optional[list[str]]:
    """DFS from ``root``; return the first back-edge cycle path, else None.

    Iterative, with the stack holding ``[node, next-dep-index]`` and ``path`` the
    current gray chain. Deps are visited in stored order, so the reported path is
    deterministic.
    """
    stack: list[list] = [[root, 0]]
    color[root] = _GRAY
    path = [root]
    while stack:
        node, i = stack[-1]
        if i >= len(deps[node]):
            color[node] = _BLACK
            stack.pop()
            path.pop()
            continue
        stack[-1][1] += 1
        nxt = deps[node][i]
        if color[nxt] == _GRAY:
            return path[path.index(nxt) :] + [nxt]
        if color[nxt] == _WHITE:
            color[nxt] = _GRAY
            stack.append([nxt, 0])
            path.append(nxt)
    return None


def _find_cycle(tasks: list[Task]) -> Optional[list[str]]:
    """Return the first dependency cycle (as an id path) in stored order, else None.

    White/gray/black DFS over ``tasks``. Only deps that reference a task *in this set*
    are followed; deps pointing outside it (unknown or rejected) are reported
    separately by :func:`_missing_dep_integrity`.
    """
    ids = {t.id for t in tasks}
    deps = {t.id: [d for d in t.deps if d in ids] for t in tasks}
    color = {t.id: _WHITE for t in tasks}
    for root in (t.id for t in tasks):
        if color[root] == _WHITE:
            cycle = _walk_from(root, deps, color)
            if cycle:
                return cycle
    return None


def _missing_dep_integrity(plan: Plan) -> list[str]:
    """Dependency integrity over *active* (non-rejected) tasks.

    Rejected tasks are omitted from the exported plan, so a dependency on one would
    render a ``depends on:`` line whose target never appears — that is an integrity
    failure, distinct from a dangling dep on a task that does not exist at all. Cycles
    and dangling deps that live only among rejected tasks do not block convergence.
    """
    active = [t for t in plan.tasks if t.status != "rejected"]
    active_ids = {t.id for t in active}
    all_ids = {t.id for t in plan.tasks}
    missing: list[str] = []
    for t in active:
        for d in t.deps:
            if d not in all_ids:
                missing.append(f"task {t.id} depends on unknown task {d}")
            elif d not in active_ids:
                missing.append(f"task {t.id} depends on rejected task {d}")
    cycle = _find_cycle(active)
    if cycle:
        missing.append("dependency cycle: " + " -> ".join(cycle))
    return missing


def dependency_blockers(plan: Plan) -> list[str]:
    """Public view of just the dependency-graph integrity blockers.

    The dangling-dep / rejected-dep / cycle subset of the full gate — without the
    coverage, acceptance, or resolution checks. ``devague plan waves`` uses this to
    refuse an unsound graph (a cycle or a dep on a missing/rejected task) while still
    emitting waves for an otherwise in-progress, not-yet-converged plan.
    """
    return _missing_dep_integrity(plan)


def _missing_risks(plan: Plan) -> list[str]:
    """Unresolved blocking risks only.

    A resolved risk stays on the plan's record for provenance (see
    ``Plan.resolve_risk``) but drops out of the gate the moment it is resolved
    (resolve-parked-vagueness t4, mirrors t3's frame-side twin).
    """
    return [
        f"blocking risk {r.id} unresolved"
        for r in plan.risks
        if r.kind == "unknown_blocking" and not r.resolved
    ]


def _parked_items(plan: Plan, targets: list[CoverageTarget]) -> list[str]:
    """Tracked, non-blocking items: unresolved risks (everything but
    unknown_blocking) plus deliberately deferred coverage targets (issue #85).

    A resolved risk is no longer open vagueness — it stays on the plan's record for
    provenance (``Plan.resolve_risk``) but should stop being advertised as parked
    (t4 AC3, mirrors t3's frame-side ``_parked_items``). A deferred target is the
    coverage-side peer: it is excluded from ``_missing_coverage``'s blockers, but
    must still surface *somewhere* distinct from "not yet covered" — this is that
    surface, labeled ``deferred:`` so it reads differently from a ``[kind] text``
    risk line at a glance.
    """
    items = [
        f"[{r.kind}] {r.text}"
        for r in plan.risks
        if r.kind != "unknown_blocking" and not r.resolved
    ]
    items += [
        f"deferred: coverage target {tg.id} ({tg.kind}) — {tg.deferred_reason}"
        for tg in targets
        if tg.deferred
    ]
    return items


def suggest_move(blocker: str) -> str:
    """Map a single plan blocker to the recommended next ``devague plan`` move."""
    if "no tasks yet" in blocker:
        return 'devague plan task "<summary>" --covers <c*/h*> --accept "<criterion>"'
    m = re.search(r"coverage target (\w+) ", blocker)
    if m:
        tid = m.group(1)
        return (
            f'cover {tid}: devague plan task "<summary>" --covers {tid} --accept "<...>"'
            f"   (or: devague plan cover <tN> --target {tid})"
        )
    m = re.search(r"task (t\d+) has no acceptance", blocker)
    if m:
        return f'devague plan accept {m.group(1)} "<acceptance criterion>"'
    m = re.search(r"task (t\d+) still proposed", blocker)
    if m:
        tid = m.group(1)
        return (
            f"this is an LLM proposal — the USER decides: "
            f"devague plan confirm {tid} (or reject {tid})"
        )
    m = re.search(r"task (t\d+) depends on (?:unknown|rejected) task (t\d+)", blocker)
    if m:
        return f"fix {m.group(1)}'s dependency on {m.group(2)} (add it, or drop the dep)"
    if "dependency cycle" in blocker:
        return "break the dependency cycle: re-point one task's --dep so the graph is acyclic"
    m = re.search(r"blocking risk (r\d+)", blocker)
    if m:
        return (
            f"resolve {m.group(1)} with a decision: "
            f'devague plan risk --resolve {m.group(1)} --decision "<the decision>"'
        )
    return "devague plan show     # inspect and decide"


def _tdd_fitness_warnings(plan: Plan) -> list[str]:
    """Non-blocking warnings that flag poor parallel/TDD fitness.

    Three deterministic, purely structural heuristics:

    1. **Missing acceptance criteria on confirmed tasks.**
       A confirmed task with zero acceptance criteria cannot be validated test-first.
       This fires even though :func:`_missing_acceptance` already raises a blocker for
       the same condition — the warning reinforces the TDD-fitness signal independently
       of the gate, so it appears in ``warnings[]`` even when the plan has not converged.
       Proposed and rejected tasks are excluded: proposed tasks are gated by the
       "still proposed" blocker; rejected tasks are not built.

    2. **Missing instruction on confirmed tasks.**
       A confirmed task with an empty instruction field lacks operator guidance for
       implementation. The warning is purely advisory and does not affect convergence;
       it reminds the operator to attach working instructions. Proposed and rejected
       tasks are excluded for the same reasons as heuristic 1.

    3. **Over-serialized dependency graph.**
       When every wave produced by :func:`~devague.plan.dependency_waves` contains
       exactly one active confirmed task AND there are at least three such tasks, the
       plan is fully serial — every task blocks the next, no fan-out is possible.
       This is the "needless single-task wave / trivial linear chain" pattern that
       wastes parallel capacity.  The threshold of 3 is deliberate: a single task is
       trivially serial (no parallelism to exploit) and a two-task chain is the minimal
       producer/consumer relationship (also not actionable).  The heuristic only counts
       **confirmed** active (non-rejected) tasks; proposed tasks are unresolved and may
       be rejected, so counting them would produce unstable warnings.

    No warning changes ``ready_for_plan`` or ``blockers``.
    """
    warnings: list[str] = []

    # Heuristic 1: confirmed task with zero acceptance criteria.
    for t in plan.tasks:
        if t.status == "confirmed" and not t.acceptance_criteria:
            warnings.append(
                f"task {t.id} has no acceptance criteria"
                " — add TDD acceptance tests before implementation"
            )

    # Heuristic 2: confirmed task with no instruction.
    for t in plan.tasks:
        if t.status == "confirmed" and not t.instruction:
            warnings.append(
                f"task {t.id} has no instruction"
                f' — attach operator guidance with `devague plan instruct {t.id} "<text>"`'
            )

    # Heuristic 3: over-serialized graph.
    active_confirmed = [t for t in plan.tasks if t.status == "confirmed"]
    if len(active_confirmed) >= 3:
        waves = dependency_waves(plan.tasks)
        # Filter to waves that contain at least one confirmed task.
        confirmed_ids = {t.id for t in active_confirmed}
        confirmed_waves = [[tid for tid in w if tid in confirmed_ids] for w in waves]
        confirmed_waves = [w for w in confirmed_waves if w]
        if confirmed_waves and all(len(w) == 1 for w in confirmed_waves):
            warnings.append(
                f"plan has {len(active_confirmed)} confirmed tasks"
                " forming a fully serial chain — consider parallelizing"
                " independent tasks into the same wave"
            )

    return warnings


def _unmet_obligation_warnings(plan: Plan, met: set[str]) -> list[str]:
    """One warning per non-rejected criterion obligation with no approved
    evidence (bvts t7) — the plan-side twin of :mod:`devague.convergence`'s S3.

    Pure: ``met`` is the set of obligation refs the caller already determined
    are discharged (:func:`devague.obligation_evidence.met_obligation_refs_for_plan`
    loads it fail-open at the CLI edge, from *this* plan's own delivery ledger).
    A rejected obligation is withdrawn and stays silent; a proposed one is
    unadjudicated but equally undischarged, so it warns.

    The text names the obligation, the task and criterion it obligates, and its
    seam, and says **untested** in as many words — a confirmed acceptance
    criterion whose behavior nothing verifies is exactly the gap this warning
    exists to make visible. Never blocking, on the same soft-rollout terms as
    the TDD-fitness heuristics above.
    """
    return [
        f"obligation {o.id} on task {o.task_id} criterion {o.criterion_index} is "
        f"untested — seam '{o.seam}' has no approved evidence for: {o.behavior}"
        for o in plan.obligations
        if o.status != "rejected" and o.id not in met
    ]


def evaluate(
    plan: Plan,
    targets: Optional[list[CoverageTarget]] = None,
    met_obligations: Optional[Iterable[str]] = None,
) -> ConvergenceResult:
    """Evaluate the plan gate against ``targets`` (defaults to the plan's snapshot).

    The CLI passes *live* targets re-derived from the current source frame so frame
    drift is caught; unit tests may omit ``targets`` to gate against the stored
    snapshot.

    ``met_obligations`` follows the same injected-state convention: the CLI
    loads it fail-open from the plan's delivery ledger and passes it in, so this
    function stays pure and filesystem-free. Omitting it means "no evidence
    state was loaded" and can only add warnings, never a blocker.
    """
    tgs = plan.targets if targets is None else targets
    met = set() if met_obligations is None else set(met_obligations)
    blockers = (
        _missing_tasks(plan)
        + _missing_coverage(plan, tgs)
        + _missing_acceptance(plan)
        + _missing_resolution(plan)
        + _missing_dep_integrity(plan)
        + _missing_risks(plan)
    )
    return ConvergenceResult(
        ready=not blockers,
        blockers=blockers,
        warnings=_tdd_fitness_warnings(plan) + _unmet_obligation_warnings(plan, met),
        parked_items=_parked_items(plan, tgs),
        required_next_moves=[suggest_move(b) for b in blockers],
    )
