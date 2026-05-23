"""Renderer: the buildable plan as markdown, derived from a converged plan + frame.

Unlike the frame renderers this is **not** registered in :mod:`devague.render` — that
registry is ``Callable[[Frame], str]`` and a plan render needs both the plan and its
source frame for context. The ``devague plan export`` command calls :func:`render_plan`
directly, so ``render.formats()`` deliberately does not list ``plan-md``.
"""

from __future__ import annotations

from typing import Optional

from devague.frame import Frame
from devague.plan import Plan, Task


def _topo_order(tasks: list[Task]) -> list[Task]:
    """Order tasks so each task's deps precede it; stable in stored order.

    Independent tasks keep their stored order. Unknown deps are ignored (reported as
    gaps by the gate). On a cycle the remaining tasks are appended in stored order so
    rendering never fails — the gate is what blocks export, not the renderer.
    """
    by_id = {t.id: t for t in tasks}
    emitted_ids: set[str] = set()
    ordered: list[Task] = []
    remaining = list(tasks)
    progress = True
    while remaining and progress:
        progress = False
        still: list[Task] = []
        for t in remaining:
            if all(d in emitted_ids or d not in by_id for d in t.deps):
                ordered.append(t)
                emitted_ids.add(t.id)
                progress = True
            else:
                still.append(t)
        remaining = still
    ordered.extend(remaining)  # cycle leftover, stored order
    return ordered


def _announcement(frame: Optional[Frame]) -> Optional[str]:
    if frame is None:
        return None
    for c in frame.claims:
        if c.kind == "announcement" and c.status == "confirmed":
            return c.text
    return None


def _task_lines(task: Task) -> list[str]:
    mark = "" if task.status == "confirmed" else f" _({task.status})_"
    body: list[str] = []
    if task.deps:
        body.append(f"- depends on: {', '.join(task.deps)}")
    if task.covers:
        body.append(f"- covers: {', '.join(task.covers)}")
    if task.acceptance_criteria:
        body.append("- acceptance:")
        body.extend(f"  - {a}" for a in task.acceptance_criteria)
    lines = [f"### {task.id} — {task.summary}{mark}"]
    if body:
        # Blank line between the heading and its list (MD022/MD032).
        lines += ["", *body]
    lines.append("")
    return lines


def render_plan(plan: Plan, frame: Optional[Frame]) -> str:
    out = [
        f"# Build Plan — {plan.title}",
        "",
        f"slug: `{plan.slug}` · status: `{plan.status}` · from frame: `{plan.frame_slug}`",
        "",
    ]
    ann = _announcement(frame)
    if ann:
        out += ["> " + ann, ""]

    tasks = [t for t in plan.tasks if t.status != "rejected"]
    if tasks:
        out += ["## Tasks", ""]
        for t in _topo_order(tasks):
            out.extend(_task_lines(t))

    if plan.risks:
        out += ["## Risks", ""]
        for r in plan.risks:
            suffix = f" (task {r.task_id})" if r.task_id else ""
            out.append(f"- [{r.kind}] {r.text}{suffix}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"
