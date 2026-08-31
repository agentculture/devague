"""Renderer: the buildable plan as markdown, derived from a converged plan + frame.

Unlike the frame renderers this is **not** registered in :mod:`devague.render` — that
registry is ``Callable[[Frame], str]`` and a plan render needs both the plan and its
source frame for context. The ``devague plan export`` command calls :func:`render_plan`
directly, so ``render.formats()`` deliberately does not list ``plan-md``.
"""

from __future__ import annotations

from typing import Optional

from devague.frame import Frame
from devague.plan import Plan, Task, criterion_obligation_drift
from devague.render._md_safety import autolink_urls, heading_safe, md_safe_text


def _verbatim(text: str) -> str:
    """Render-only escaping for free-form verbatim body text (#64 + #87): wrap
    bare URLs first (MD034), then apply the identifier/control-char escaper
    (MD037/MD050) on top of the result. Plain prose and plain URLs — the common
    cases, and the ones under test — are unaffected by the order; the one
    combination this does not special-case is a URL whose host/path itself
    contains an underscore, since ``autolink_urls``'s ``<...>`` wrapper is not
    code-span-aware the way ``md_safe_text``'s own carving is.
    """
    return md_safe_text(autolink_urls(text))


def _verbatim_heading(text: str) -> str:
    """Like :func:`_verbatim` but for heading text: autolink + strip
    markdownlint's MD026 trailing punctuation (``heading_safe``), then wrap any
    underscore/dunder identifiers in code spans on top (MD037/MD050) — the
    #87-comment MD050 regression this task exists to close for task headings.
    """
    return md_safe_text(heading_safe(text))


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


def _obligation_lines(task: Task, obligations) -> list[str]:
    """Obligations filed against ``task`` (bvts t4), nested under it the same
    way acceptance criteria already are: every obligation renders here
    regardless of status, with a drift marker computed via the pure
    :func:`devague.plan.criterion_obligation_drift` — never re-derived here —
    when the task's live acceptance-criterion text no longer matches the
    obligation's filed snapshot.
    """
    lines = []
    for o in [ob for ob in obligations if ob.task_id == task.id]:
        om = "" if o.status == "approved" else f" _({o.status})_"
        drift = " — ⚠ drifted" if criterion_obligation_drift(o, task) else ""
        lines.append(
            f"- obligation: `{o.id}` (criterion {o.criterion_index}) "
            f"[{_verbatim(o.seam)}] {_verbatim(o.behavior)}{om}{drift}"
        )
    return lines


def _task_lines(task: Task, obligations=()) -> list[str]:
    mark = "" if task.status == "confirmed" else f" _({task.status})_"
    body: list[str] = []
    if task.instruction:
        # Verbatim working instruction — never fabricated filler when absent (#53
        # t9), mirroring t6's nested ``- instruction:`` bullet in spec_md.py /
        # frame_md.py. A task is a heading rather than a claim bullet, so the
        # instruction renders as the first body bullet, immediately under it.
        body.append(f"- instruction: {_verbatim(task.instruction)}")
    if task.deps:
        body.append(f"- depends on: {', '.join(task.deps)}")
    if task.covers:
        body.append(f"- covers: {', '.join(task.covers)}")
    if task.acceptance_criteria:
        body.append("- acceptance:")
        body.extend(f"  - {_verbatim(a)}" for a in task.acceptance_criteria)
    body.extend(_obligation_lines(task, obligations))
    lines = [f"### {task.id} — {_verbatim_heading(task.summary)}{mark}"]
    if body:
        # Blank line between the heading and its list (MD022/MD032).
        lines += ["", *body]
    lines.append("")
    return lines


def _deferred_targets_lines(plan: Plan) -> list[str]:
    """The ``## Deferred targets`` section (issue #85): every coverage target
    deliberately excluded from this plan's gate (``plan defer``), named with its
    reason so the exclusion is visible in the exported artifact rather than
    implied by absence. Renders nothing when the plan has no deferred targets.
    """
    deferred = [tg for tg in plan.targets if tg.deferred]
    if not deferred:
        return []
    out = ["## Deferred targets", ""]
    for tg in deferred:
        out.append(
            f"- `{tg.id}` ({tg.kind}): {_verbatim(tg.text)}"
            f" — deferred: {_verbatim(tg.deferred_reason)}"
        )
    return out + [""]


def render_plan(plan: Plan, frame: Optional[Frame]) -> str:
    out = [
        f"# Build Plan — {_verbatim_heading(plan.title)}",
        "",
        f"slug: `{plan.slug}` · status: `{plan.status}` · from frame: `{plan.frame_slug}`",
        "",
    ]
    ann = _announcement(frame)
    if ann:
        out += ["> " + _verbatim(ann), ""]

    tasks = [t for t in plan.tasks if t.status != "rejected"]
    if tasks:
        out += ["## Tasks", ""]
        for t in _topo_order(tasks):
            out.extend(_task_lines(t, plan.obligations))

    out += _deferred_targets_lines(plan)

    if plan.risks:
        out += ["## Risks", ""]
        for r in plan.risks:
            suffix = f" (task {r.task_id})" if r.task_id else ""
            out.append(f"- [{r.kind}] {_verbatim(r.text)}{suffix}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"
