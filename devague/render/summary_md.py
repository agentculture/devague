"""Renderer: the eight-section delivery-summary skeleton, from state alone (#53-esd t4).

Structural peer of :mod:`devague.render.plan_md` — but where a plan render fills in
what was *contracted*, this renderer fills in only what is *mechanically derivable*
from a plan, its live source frame, and its delivery (deviation) store. It never
claims anything is done: run status, per-task delivery status, evidence, and
delivery claims all stay explicit ``<fill: ...>`` placeholders (backticked so they
render as literal code spans, not inline HTML — MD033-safe) until a human fills
them in. This is the no-overclaim boundary the whole feature exists to hold.

Section names and order are pinned to the eight-section template in
``.claude/skills/summarize-delivery/SKILL.md`` — Intent, Planned Work, Actual
Delivery, Mid-work Decisions, Drift From Plan, Evidence, Delivery Claims,
Remaining Work / Follow-up. Only two sections are pre-filled from real state
beyond the plan's task list: Mid-work Decisions and Drift From Plan quote
**approved** deviation records by id; a ``proposed`` deviation is never rendered
as if it were an approved decision — it surfaces (if at all) under an explicit
"pending approval" line, never folded into the approved lists.

``--pr`` mode (see :func:`render_pr_summary`) is a separate, condensed rendering
for a PR body: title, announcement, the wave/task map, approved deviations, and a
pointer to the ``docs/deliveries/<date>-<slug>.md`` artifact this skeleton seeds.

Pure functions of ``(Plan, Optional[Frame], Delivery)`` — no I/O, no mutation.
"""

from __future__ import annotations

import time
from typing import Optional

from devague.delivery import Delivery, DeviationRecord
from devague.frame import Frame
from devague.plan import Plan, dependency_waves
from devague.render._md_safety import autolink_urls, heading_safe

RUN_STATUS_PLACEHOLDER = "<complete | partial | failed>"

# SonarCloud python:S1192 — this literal was duplicated across three render
# paths (Planned Work / Actual Delivery / the --pr wave-task-map); one
# constant backs all of them now.
NO_TASKS_PLACEHOLDER = "(no tasks recorded on this plan)"

# Kept local (not imported from devague.cli._paths) so this render module has no
# dependency on the CLI layer — the same layering plan_md.py/spec_md.py already
# keep. Mirrors cli/_paths.py's UNDATED_PREFIX sentinel and date-validity check.
_UNDATED_PREFIX = "0000-00-00"


def _escape_table_cell(text: str) -> str:
    """Make ``text`` safe to interpolate into a single GFM markdown-table cell.

    A raw ``|`` inside a cell is parsed as an extra column separator, silently
    corrupting the row's column count; a raw newline breaks the row onto a
    second line GFM does not treat as part of the same row. Both are
    neutralised — the pipe is escaped (``\\|``, rendered as a literal ``|``),
    and any newline is flattened to a space — so free-form prose interpolated
    into a table cell (a deviation's ``reason`` in :func:`_drift_lines`) can
    never break the table it renders into (#72 review, Q2).
    """
    return text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _date_prefix(created: str) -> str:
    date = (created or "")[:10]
    try:
        time.strptime(date, "%Y-%m-%d")
        return date
    except ValueError:
        return _UNDATED_PREFIX


def _deliveries_pointer(plan: Plan) -> str:
    return f"docs/deliveries/{_date_prefix(plan.created)}-{plan.slug}.md"


def _confirmed_claim_texts(frame: Optional[Frame], kind: str) -> list[str]:
    if frame is None:
        return []
    return [c.text for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _confirmed_claim_text(frame: Optional[Frame], kind: str) -> Optional[str]:
    texts = _confirmed_claim_texts(frame, kind)
    return texts[0] if texts else None


def _approved(delivery: Delivery) -> list[DeviationRecord]:
    return [d for d in delivery.deviations if d.status == "approved"]


def _pending(delivery: Delivery) -> list[DeviationRecord]:
    return [d for d in delivery.deviations if d.status == "proposed"]


# ── markdown sections ────────────────────────────────────────────────────────
def _intent_lines(plan: Plan, frame: Optional[Frame]) -> list[str]:
    lines = ["## Intent", ""]
    if frame is None:
        lines.append(
            f"No source frame available (`{plan.frame_slug}` could not be loaded) — "
            "fill in the intent manually."
        )
        lines.append("")
        return lines
    ann = _confirmed_claim_text(frame, "announcement")
    if ann:
        lines.append("> " + autolink_urls(ann))
    else:
        lines.append("(no confirmed announcement recorded in the source frame)")
    afters = _confirmed_claim_texts(frame, "after_state")
    if afters:
        lines.append("")
        lines.append("After: " + "; ".join(autolink_urls(a) for a in afters))
    lines.append("")
    return lines


def _planned_work_lines(plan: Plan) -> list[str]:
    lines = ["## Planned Work", ""]
    if not plan.tasks:
        lines.append(NO_TASKS_PLACEHOLDER)
        lines.append("")
        return lines
    for t in plan.tasks:
        mark = "" if t.status == "confirmed" else f" _({t.status})_"
        lines.append(f"- `{t.id}` — {autolink_urls(t.summary)}{mark}")
    lines.append("")
    return lines


def _actual_delivery_lines(plan: Plan) -> list[str]:
    lines = ["## Actual Delivery", ""]
    if not plan.tasks:
        lines.append(NO_TASKS_PLACEHOLDER)
        lines.append("")
        return lines
    lines.append("| Plan task | Status | What actually landed |")
    lines.append("|-----------|--------|----------------------|")
    for t in plan.tasks:
        lines.append(f"| `{t.id}` | `<fill: status>` | `<fill: what landed>` |")
    lines.append("")
    return lines


def _mid_work_lines(delivery: Delivery) -> list[str]:
    lines = ["## Mid-work Decisions", ""]
    approved = _approved(delivery)
    pending = _pending(delivery)
    if not approved and not pending:
        lines.append("(no deviations recorded yet)")
        lines.append("")
        return lines
    for d in approved:
        lines.append(f"- `{d.id}` — {autolink_urls(d.what)} — {autolink_urls(d.reason)}")
    if pending:
        ids = ", ".join(f"`{d.id}`" for d in pending)
        lines.append(f"- pending approval (not yet a decision): {ids}")
    lines.append("")
    return lines


def _drift_lines(delivery: Delivery) -> list[str]:
    lines = ["## Drift From Plan", ""]
    approved = _approved(delivery)
    if not approved:
        lines.append(
            "no approved deviation records yet — record drift via `devague deviate` "
            "before this section can be filled in"
        )
        lines.append("")
        return lines
    lines.append("| Plan item | Reason for divergence | Classification |")
    lines.append("|-----------|------------------------|-----------------|")
    for d in approved:
        classification = f"`{d.classification}`" if d.classification else "`<fill: classification>`"
        # d.task_ref/d.id are backticked refs; d.reason is free-form prose --
        # _escape_table_cell keeps a raw '|' or newline in it from corrupting
        # the row (#72 review, Q2).
        reason = _escape_table_cell(autolink_urls(d.reason))
        task_ref = _escape_table_cell(d.task_ref)
        did = _escape_table_cell(d.id)
        lines.append(f"| `{task_ref}` (`{did}`) | {reason} | {classification} |")
    lines.append("")
    return lines


def _evidence_lines() -> list[str]:
    return [
        "## Evidence",
        "",
        "- tests: `<fill: pytest node id>` — `<fill: pass | fail>`",
        "- lint: `<fill: command>` — `<fill: result>`",
        "- commits: `<fill: sha>..<fill: sha>`",
        "- PRs / issues: `<fill: #NN>`",
        "",
    ]


def _delivery_claims_lines() -> list[str]:
    return [
        "## Delivery Claims",
        "",
        "| Claim | Confidence | Evidence |",
        "|-------|------------|----------|",
        "| `<fill: what was delivered>` | `<fill: confidence>` | `<fill: evidence>` |",
        "",
    ]


def _remaining_work_lines() -> list[str]:
    return [
        "## Remaining Work / Follow-up",
        "",
        "- `<fill: remaining item>` — `<fill: next step / owner>`",
        "",
    ]


def render_summary(plan: Plan, frame: Optional[Frame], delivery: Delivery) -> str:
    """The eight-section delivery-summary skeleton, pre-filled from state alone.

    Deterministic and read-only: calling this twice on unchanged ``(plan, frame,
    delivery)`` produces byte-identical output, and nothing here writes to disk.
    """
    date = _date_prefix(plan.created)
    out = [
        f"# Delivery Summary — {heading_safe(plan.title)}",
        "",
        f"plan: `{plan.slug}` · run: `{RUN_STATUS_PLACEHOLDER}` · date: `{date}`",
        f"baseline: `devague plan ({plan.slug})`",
        "",
    ]
    out += _intent_lines(plan, frame)
    out += _planned_work_lines(plan)
    out += _actual_delivery_lines(plan)
    out += _mid_work_lines(delivery)
    out += _drift_lines(delivery)
    out += _evidence_lines()
    out += _delivery_claims_lines()
    out += _remaining_work_lines()
    return "\n".join(out).rstrip() + "\n"


def summary_data(plan: Plan, frame: Optional[Frame], delivery: Delivery) -> dict:
    """The structured (``--json``) equivalent of :func:`render_summary`.

    Carries the same pre-filled data and the same explicit placeholder markers —
    a consumer parsing JSON gets no more certainty than a reader of the markdown.
    """
    approved = _approved(delivery)
    pending = _pending(delivery)
    return {
        "plan": plan.slug,
        "title": plan.title,
        "run_status": RUN_STATUS_PLACEHOLDER,
        "date": _date_prefix(plan.created),
        "baseline": f"devague plan ({plan.slug})",
        "frame_available": frame is not None,
        "sections": {
            "intent": {
                "announcement": _confirmed_claim_text(frame, "announcement"),
                "after_state": _confirmed_claim_texts(frame, "after_state"),
            },
            "planned_work": [
                {"id": t.id, "summary": t.summary, "status": t.status} for t in plan.tasks
            ],
            "actual_delivery": [
                {"id": t.id, "status": "<fill: status>", "what_landed": "<fill: what landed>"}
                for t in plan.tasks
            ],
            "mid_work_decisions": [
                {"id": d.id, "what": d.what, "reason": d.reason} for d in approved
            ],
            "drift_from_plan": [
                {
                    "task": d.task_ref,
                    "deviation": d.id,
                    "reason": d.reason,
                    "classification": d.classification or "<fill: classification>",
                }
                for d in approved
            ],
            "pending_deviations": [d.id for d in pending],
            "evidence": "<fill: evidence>",
            "delivery_claims": "<fill: delivery claims>",
            "remaining_work": "<fill: remaining work>",
        },
    }


# ── --pr mode: condensed PR-body skeleton ────────────────────────────────────
def _wave_task_map_lines(plan: Plan) -> list[str]:
    lines = ["## Wave / Task Map", ""]
    waves = dependency_waves(plan.tasks)
    if not waves:
        lines.append(NO_TASKS_PLACEHOLDER)
        lines.append("")
        return lines
    for i, wave in enumerate(waves):
        lines.append(f"- wave {i}: " + ", ".join(f"`{tid}`" for tid in wave))
    by_id = {t.id: t for t in plan.tasks}
    lines.append("")
    for wave in waves:
        for tid in wave:
            t = by_id.get(tid)
            if t is not None:
                lines.append(f"- `{t.id}` — {autolink_urls(t.summary)}")
    lines.append("")
    return lines


def _approved_deviations_lines(delivery: Delivery) -> list[str]:
    lines = ["## Approved Deviations", ""]
    approved = _approved(delivery)
    if not approved:
        lines.append("(none recorded)")
        lines.append("")
        return lines
    for d in approved:
        lines.append(
            f"- `{d.id}` (task `{d.task_ref}`) — {autolink_urls(d.what)}: {autolink_urls(d.reason)}"
        )
    lines.append("")
    return lines


def render_pr_summary(plan: Plan, frame: Optional[Frame], delivery: Delivery) -> str:
    """The condensed ``--pr`` skeleton: title, announcement, wave/task map,
    approved deviations, and a pointer to the ``docs/deliveries`` artifact.
    """
    out = [f"# {heading_safe(plan.title)}", ""]
    ann = _confirmed_claim_text(frame, "announcement")
    if ann:
        out += ["> " + autolink_urls(ann), ""]
    out += _wave_task_map_lines(plan)
    out += _approved_deviations_lines(delivery)
    out += [f"Delivery summary: `{_deliveries_pointer(plan)}`", ""]
    return "\n".join(out).rstrip() + "\n"


def pr_data(plan: Plan, frame: Optional[Frame], delivery: Delivery) -> dict:
    """The structured (``--json``) equivalent of :func:`render_pr_summary`."""
    waves = dependency_waves(plan.tasks)
    by_id = {t.id: t for t in plan.tasks}
    approved = _approved(delivery)
    return {
        "plan": plan.slug,
        "title": plan.title,
        "announcement": _confirmed_claim_text(frame, "announcement"),
        "waves": waves,
        "tasks": {tid: by_id[tid].summary for wave in waves for tid in wave if tid in by_id},
        "approved_deviations": [
            {"id": d.id, "task": d.task_ref, "what": d.what, "reason": d.reason} for d in approved
        ],
        "deliveries_pointer": _deliveries_pointer(plan),
    }
