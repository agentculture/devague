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


def _find_cycle(plan: Plan) -> Optional[list[str]]:
    """Return the first dependency cycle (as an id path) in stored order, else None.

    Iterative DFS with white/gray/black colouring; tasks and their deps are visited in
    stored order so the reported path is deterministic. Only deps that reference a real
    task are followed (dangling deps are reported separately).
    """
    ids = {t.id for t in plan.tasks}
    deps = {t.id: [d for d in t.deps if d in ids] for t in plan.tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.id: WHITE for t in plan.tasks}

    for root in (t.id for t in plan.tasks):
        if color[root] != WHITE:
            continue
        # stack holds (node, index-into-its-deps); `path` is the current gray chain.
        stack: list[list] = [[root, 0]]
        color[root] = GRAY
        path = [root]
        while stack:
            node, i = stack[-1]
            if i < len(deps[node]):
                stack[-1][1] += 1
                nxt = deps[node][i]
                if color[nxt] == GRAY:
                    return path[path.index(nxt) :] + [nxt]
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append([nxt, 0])
                    path.append(nxt)
            else:
                color[node] = BLACK
                stack.pop()
                path.pop()
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
