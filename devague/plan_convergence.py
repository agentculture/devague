"""The plan convergence gate: is a plan solid enough to export a buildable plan?

The peer of :mod:`devague.convergence`. A plan converges when every coverage target
is covered by a confirmed task, every confirmed task carries acceptance criteria, the
dependency graph is sound (no dangling refs, no cycles), nothing is left proposed, and
no blocking risk remains. Reuses :class:`devague.convergence.ConvergenceResult` so both
engines report the same structured ``{ready, blockers, warnings, parked_items,
required_next_moves}`` shape (the CLI serializes ``ready`` as ``ready_for_plan``).
"""

from __future__ import annotations

import re
from typing import Optional

from devague.convergence import ConvergenceResult
from devague.plan import CoverageTarget, Plan, Task


def _missing_tasks(plan: Plan) -> list[str]:
    if not plan.tasks:
        return ["no tasks yet (add at least one with 'plan task')"]
    return []


def _missing_coverage(plan: Plan, targets: list[CoverageTarget]) -> list[str]:
    covered = {tid for t in plan.tasks if t.status == "confirmed" for tid in t.covers}
    return [
        f"coverage target {tg.id} ({tg.kind}) has no confirmed task"
        for tg in targets
        if tg.id not in covered
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
    return [f"blocking risk {r.id} unresolved" for r in plan.risks if r.kind == "unknown_blocking"]


def _parked_items(plan: Plan) -> list[str]:
    """Tracked, non-blocking risks (everything but unknown_blocking)."""
    return [f"[{r.kind}] {r.text}" for r in plan.risks if r.kind != "unknown_blocking"]


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
        return f"resolve {m.group(1)}: cover it with a task, or re-record it as non-blocking"
    return "devague plan show     # inspect and decide"


def evaluate(plan: Plan, targets: Optional[list[CoverageTarget]] = None) -> ConvergenceResult:
    """Evaluate the plan gate against ``targets`` (defaults to the plan's snapshot).

    The CLI passes *live* targets re-derived from the current source frame so frame
    drift is caught; unit tests may omit ``targets`` to gate against the stored
    snapshot.
    """
    tgs = plan.targets if targets is None else targets
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
        parked_items=_parked_items(plan),
        required_next_moves=[suggest_move(b) for b in blockers],
    )
