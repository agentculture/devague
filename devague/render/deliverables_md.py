"""Renderer: the read-only deliverables view — "what do we have in the end?" (#70).

At the assign-to-workforce go/no-go, a human approves a workforce fan-out without
seeing the world the plan actually produces. ``devague plan deliverables`` answers
that question, synthesized *only* from existing frame/plan state: the live source
frame's confirmed ``announcement`` / ``after_state`` / ``success_signal`` claims
(verbatim), the plan's terminal tasks (:func:`devague.plan.terminal_tasks` — active
tasks no other active task depends on) with their acceptance criteria, and surviving
open items (the frame's non-blocking parked vagueness plus the plan's non-blocking
risks).

Like :mod:`devague.render.plan_md` this is **not** registered in the
``devague.render`` registry (that registry is ``Callable[[Frame], str]``; a
deliverables render needs the plan too) — ``devague plan deliverables`` calls
:func:`render_deliverables` directly. Unlike every other exported artifact, this view
never gates on convergence: an unconverged plan still renders, with an explicit
banner instead of a refusal (issue #20 — Devague describes state, it does not judge
whether the human should proceed).
"""

from __future__ import annotations

from devague.frame import Claim, Frame
from devague.plan import Plan, Task, terminal_tasks
from devague.render._md_safety import autolink_urls, heading_safe

NOT_CONVERGED_BANNER = "note: plan has not converged — this is a preview, not a commitment"

_WORLD_AFTER_KINDS = (
    ("announcement", "Announcement"),
    ("after_state", "After state"),
    ("success_signal", "Success signals"),
)


def _confirmed(frame: Frame, kind: str) -> list[Claim]:
    return [c for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _world_after_section(frame: Frame) -> list[str]:
    """Confirmed announcement / after_state / success_signal claims, verbatim."""
    out: list[str] = []
    for kind, heading in _WORLD_AFTER_KINDS:
        claims = _confirmed(frame, kind)
        if not claims:
            continue
        out.append(f"## {heading}")
        out.append("")
        out.extend(f"- {autolink_urls(c.text)}" for c in claims)
        out.append("")
    return out


def _task_lines(task: Task) -> list[str]:
    lines = [f"- `{task.id}` — {autolink_urls(task.summary)}"]
    lines.extend(f"  - {autolink_urls(a)}" for a in task.acceptance_criteria)
    return lines


def _terminal_tasks_section(plan: Plan) -> list[str]:
    terminal = terminal_tasks(plan.tasks)
    if not terminal:
        return []
    out = ["## Terminal tasks", ""]
    for t in terminal:
        out.extend(_task_lines(t))
    out.append("")
    return out


def _open_items_section(frame: Frame, plan: Plan) -> list[str]:
    """Surviving open items: non-blocking frame vagueness + non-blocking plan risks.

    ``unknown_blocking`` items are excluded on both sides — a genuinely blocking item
    would have kept the frame/plan from converging in the first place, so what
    survives here is exactly the tracked-but-non-blocking uncertainty (mirrors
    ``convergence._parked_items`` / ``plan_convergence._parked_items``).
    """
    items = [
        f"[{v.kind}] {autolink_urls(v.text)}"
        for v in frame.open_vagueness
        if v.kind != "unknown_blocking"
    ]
    items += [
        f"[{r.kind}] {autolink_urls(r.text)}" for r in plan.risks if r.kind != "unknown_blocking"
    ]
    if not items:
        return []
    out = ["## Open items", ""]
    out.extend(f"- {i}" for i in items)
    out.append("")
    return out


def render_deliverables(plan: Plan, frame: Frame, *, converged: bool) -> str:
    """Render the deliverables view. Never refuses: an unconverged plan still
    renders, with :data:`NOT_CONVERGED_BANNER` at the top instead of a gate error.
    """
    out = [f"# Deliverables — {heading_safe(plan.title)}", ""]
    if not converged:
        out.append(NOT_CONVERGED_BANNER)
        out.append("")
    out.extend(_world_after_section(frame))
    out.extend(_terminal_tasks_section(plan))
    out.extend(_open_items_section(frame, plan))
    return "\n".join(out).rstrip() + "\n"
