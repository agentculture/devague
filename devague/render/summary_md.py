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
from devague.plan import Plan, Task, dependency_waves
from devague.render._md_safety import autolink_urls, heading_safe, md_safe_text

RUN_STATUS_PLACEHOLDER = "<complete | partial | failed>"

# SonarCloud python:S1192 — this literal was duplicated across three render
# paths (Planned Work / Actual Delivery / the --pr wave-task-map); one
# constant backs all of them now.
NO_TASKS_PLACEHOLDER = "(no tasks recorded on this plan)"

# Kept local (not imported from devague.cli._paths) so this render module has no
# dependency on the CLI layer — the same layering plan_md.py/spec_md.py already
# keep. Mirrors cli/_paths.py's UNDATED_PREFIX sentinel and date-validity check.
_UNDATED_PREFIX = "0000-00-00"


def _verbatim(text: str) -> str:
    """Render-time markdown safety for one field of free-form verbatim prose
    (task summaries, deviation ``what``/``reason``, announcement/after-state
    claim text): autolink any bare URL (MD034), then escape/wrap markdown
    control characters and underscore-bearing identifiers (MD037/MD050, #87's
    ``md_safe_text``). Never applied to the JSON (``--json``) views
    (:func:`summary_data`/:func:`pr_data`) — those mirror the underlying data
    verbatim, the same way the frame/plan JSON stores are never touched by
    rendering (#87's round-trip-safety rule)."""
    return md_safe_text(autolink_urls(text))


def _confirmed_tasks(plan: Plan) -> list[Task]:
    """The tasks a delivery summary is scoped to (#88).

    A ``rejected`` task is planning history — visible in ``devague plan
    show``, never padded into an accountability artifact about what shipped.
    A ``proposed`` task is still under adjudication: neither the confirmed
    contract nor an explicit rejection, so folding it into either list (or
    into the rejected count below) would misrepresent an open decision as a
    closed one. Both statuses are therefore silently excluded from Planned
    Work / Actual Delivery / :func:`summary_data` — only a confirmed task is
    part of the contract this artifact reports against.
    """
    return [t for t in plan.tasks if t.status == "confirmed"]


def _rejected_task_ids(plan: Plan) -> list[str]:
    return [t.id for t in plan.tasks if t.status == "rejected"]


def _rejected_count_line(plan: Plan) -> Optional[str]:
    """A single line preserving the fact of rejection without padding the
    Planned Work / Actual Delivery listings with it (#88's suggested
    resolution). ``None`` when nothing was rejected — a clean plan gets no
    noise line at all.
    """
    n = len(_rejected_task_ids(plan))
    if not n:
        return None
    noun = "task" if n == 1 else "tasks"
    verb = "was" if n == 1 else "were"
    return f"{n} {noun} {verb} rejected during planning — see `devague plan show`."


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
        lines.append("> " + _verbatim(ann))
    else:
        lines.append("(no confirmed announcement recorded in the source frame)")
    afters = _confirmed_claim_texts(frame, "after_state")
    if afters:
        lines.append("")
        lines.append("After: " + "; ".join(_verbatim(a) for a in afters))
    lines.append("")
    return lines


def _planned_work_lines(plan: Plan) -> list[str]:
    """Confirmed tasks only (#88) — the confirmed contract, not planning
    history (rejected) or open proposals (proposed). A single line preserves
    the rejected count without padding the list; see :func:`_confirmed_tasks`
    and :func:`_rejected_count_line`."""
    lines = ["## Planned Work", ""]
    confirmed = _confirmed_tasks(plan)
    if not confirmed:
        lines.append(NO_TASKS_PLACEHOLDER)
    else:
        for t in confirmed:
            lines.append(f"- `{t.id}` — {_verbatim(t.summary)}")
    rejected_line = _rejected_count_line(plan)
    if rejected_line:
        # Blank line first: MD032 wants a list (when `confirmed` is non-empty)
        # surrounded by blank lines, and this plain sentence is not itself a
        # list item.
        lines.append("")
        lines.append(rejected_line)
    lines.append("")
    return lines


def _actual_delivery_lines(plan: Plan) -> list[str]:
    """One row per confirmed task (#88) — a rejected or still-proposed task is
    never paired with a ``<fill: status>`` placeholder, which would invite
    recording a planning decision (or an open one) as a delivery failure."""
    lines = ["## Actual Delivery", ""]
    confirmed = _confirmed_tasks(plan)
    if not confirmed:
        lines.append(NO_TASKS_PLACEHOLDER)
        lines.append("")
        return lines
    lines.append("| Plan task | Status | What actually landed |")
    lines.append("|-----------|--------|----------------------|")
    for t in confirmed:
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
        lines.append(f"- `{d.id}` — {_verbatim(d.what)} — {_verbatim(d.reason)}")
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
        reason = _escape_table_cell(_verbatim(d.reason))
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


def _approved_lapses(frame: Optional[Frame]):
    lapses = [] if frame is None else frame.lapses
    return [r for r in lapses if r.status == "approved"]


def _pending_lapses(frame: Optional[Frame]):
    lapses = [] if frame is None else frame.lapses
    return [r for r in lapses if r.status == "proposed"]


def _lapse_evidence_lines(frame: Optional[Frame]) -> list[str]:
    """Approved reasoning-degradation lapses (``Frame.lapses``, issue #97 t1)
    rendered as evidence grounding the Delivery Claims confidence column,
    following the exact approved/pending/rejected discipline
    :func:`_mid_work_lines` / :func:`_drift_lines` already apply to deviation
    records: approved entries render fully in a small table (escaped the same
    way :func:`_drift_lines` escapes free-form ``reason`` text — a raw ``|``
    or newline in a lapse's ``what`` must not corrupt the table), a proposed
    (not-yet-adjudicated) entry surfaces only as a visibly pending id, and a
    rejected entry is omitted entirely.

    A frame with no lapses at all — or no frame, a degraded load (acceptance
    criterion 4) — adds nothing here, leaving the Delivery Claims table's
    existing hardcoded placeholder row as the section's only content,
    unchanged: no new failure mode from a missing/lapse-free frame.
    """
    approved = _approved_lapses(frame)
    pending = _pending_lapses(frame)
    if not approved and not pending:
        return []
    lines = ["Lapse ledger evidence:", ""]
    if approved:
        lines.append("| Lapse | Code | What |")
        lines.append("|-------|------|------|")
        for r in approved:
            code = _escape_table_cell(r.code)
            what = _escape_table_cell(_verbatim(r.what))
            lines.append(f"| `{r.id}` | `{code}` | {what} |")
        lines.append("")
    if pending:
        ids = ", ".join(f"`{r.id}`" for r in pending)
        lines.append(f"pending approval (not yet evidence): {ids}")
        lines.append("")
    return lines


def _delivery_claims_lines(frame: Optional[Frame]) -> list[str]:
    lines = [
        "## Delivery Claims",
        "",
        "| Claim | Confidence | Evidence |",
        "|-------|------------|----------|",
        "| `<fill: what was delivered>` | `<fill: confidence>` | `<fill: evidence>` |",
        "",
    ]
    lines += _lapse_evidence_lines(frame)
    return lines


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
    out += _delivery_claims_lines(frame)
    out += _remaining_work_lines()
    return "\n".join(out).rstrip() + "\n"


def summary_data(plan: Plan, frame: Optional[Frame], delivery: Delivery) -> dict:
    """The structured (``--json``) equivalent of :func:`render_summary`.

    Carries the same pre-filled data and the same explicit placeholder markers —
    a consumer parsing JSON gets no more certainty than a reader of the markdown.
    """
    approved = _approved(delivery)
    pending = _pending(delivery)
    confirmed = _confirmed_tasks(plan)
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
            # Confirmed tasks only (#88) — see _confirmed_tasks' docstring: a
            # rejected task is planning history and a proposed one is still
            # undecided, so neither belongs in the delivery contract's task
            # lists. rejected_tasks (below) is the JSON parity for the
            # markdown's single rejected-count line — the ids, not just a
            # count, mirroring how pending_deviations carries ids rather than
            # a bare number.
            "planned_work": [
                {"id": t.id, "summary": t.summary, "status": t.status} for t in confirmed
            ],
            "actual_delivery": [
                {"id": t.id, "status": "<fill: status>", "what_landed": "<fill: what landed>"}
                for t in confirmed
            ],
            "rejected_tasks": _rejected_task_ids(plan),
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
            # JSON parity for _lapse_evidence_lines: approved lapses carry
            # their full evidence triple, a pending one is only its id (the
            # "not yet evidence" marker, mirroring pending_deviations above);
            # a rejected lapse is absent from both lists, same as the render.
            "lapse_evidence": {
                "approved": [
                    {"id": r.id, "code": r.code, "what": r.what} for r in _approved_lapses(frame)
                ],
                "pending": [r.id for r in _pending_lapses(frame)],
            },
            "remaining_work": "<fill: remaining work>",
        },
    }


# ── --pr mode: condensed PR-body skeleton ────────────────────────────────────
def _wave_task_map_lines(plan: Plan) -> list[str]:
    """``dependency_waves`` already excludes rejected tasks (plan.py) — this is
    scheduling metadata (what *could* run), not the delivery contract, so it
    intentionally keeps including ``proposed`` tasks unlike Planned Work /
    Actual Delivery above (#88's instruction: "--pr needs no [filtering]
    change")."""
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
                lines.append(f"- `{t.id}` — {_verbatim(t.summary)}")
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
            f"- `{d.id}` (task `{d.task_ref}`) — {_verbatim(d.what)}: {_verbatim(d.reason)}"
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
        out += ["> " + _verbatim(ann), ""]
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
