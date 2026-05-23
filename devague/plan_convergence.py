"""The plan convergence gate: is a plan solid enough to export a buildable plan?

The peer of :mod:`devague.convergence`. A plan converges when every coverage target
is covered by a confirmed task, every confirmed task carries acceptance criteria, the
dependency graph is sound (no dangling refs, no cycles), nothing is left proposed, and
no blocking risk remains. Reuses :class:`devague.convergence.ConvergenceResult` so both
engines report the same ``{passed, missing}`` shape.
"""

from __future__ import annotations

from typing import Optional

from devague.convergence import ConvergenceResult
from devague.plan import CoverageTarget, Plan


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


def _find_cycle(plan: Plan) -> Optional[list[str]]:
    """Return the first dependency cycle (as an id path) in stored order, else None.

    White/gray/black DFS over the dep graph. Only deps that reference a real task are
    followed (dangling deps are reported separately).
    """
    ids = {t.id for t in plan.tasks}
    deps = {t.id: [d for d in t.deps if d in ids] for t in plan.tasks}
    color = {t.id: _WHITE for t in plan.tasks}
    for root in (t.id for t in plan.tasks):
        if color[root] == _WHITE:
            cycle = _walk_from(root, deps, color)
            if cycle:
                return cycle
    return None


def _missing_dep_integrity(plan: Plan) -> list[str]:
    ids = {t.id for t in plan.tasks}
    missing = [
        f"task {t.id} depends on unknown task {d}"
        for t in plan.tasks
        for d in t.deps
        if d not in ids
    ]
    cycle = _find_cycle(plan)
    if cycle:
        missing.append("dependency cycle: " + " -> ".join(cycle))
    return missing


def _missing_risks(plan: Plan) -> list[str]:
    return [f"blocking risk {r.id} unresolved" for r in plan.risks if r.kind == "unknown_blocking"]


def evaluate(plan: Plan, targets: Optional[list[CoverageTarget]] = None) -> ConvergenceResult:
    """Evaluate the plan gate against ``targets`` (defaults to the plan's snapshot).

    The CLI passes *live* targets re-derived from the current source frame so frame
    drift is caught; unit tests may omit ``targets`` to gate against the stored
    snapshot.
    """
    tgs = plan.targets if targets is None else targets
    missing = (
        _missing_tasks(plan)
        + _missing_coverage(plan, tgs)
        + _missing_acceptance(plan)
        + _missing_resolution(plan)
        + _missing_dep_integrity(plan)
        + _missing_risks(plan)
    )
    return ConvergenceResult(passed=not missing, missing=missing)
