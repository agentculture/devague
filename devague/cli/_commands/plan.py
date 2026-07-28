"""``devague plan`` — the plan engine: turn a converged spec into a buildable plan.

This is the structural peer of the frame moves, exposed as a nested subcommand group
(``devague plan <move>``) so it never collides with the flat frame verbs. A plan is
seeded from a *converged* frame; tasks must collectively cover every coverage target
(the frame's confirmed claims + honesty conditions), carry acceptance criteria, and
form an acyclic dependency graph before the plan converges and can export.

The convergence gate is re-evaluated against the **live** source frame every time, so
a frame that changed or regressed after the plan was seeded is caught (frame drift).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from devague import plan_store, store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve as resolve_frame
from devague.cli._output import emit_diagnostic, emit_result
from devague.cli._paths import dated_name
from devague.cli._plans import resolve_plan
from devague.cli._status import StatusLabels, emit_empty, emit_status
from devague.convergence import evaluate as evaluate_frame
from devague.frame import Frame
from devague.plan import (
    RISK_KINDS,
    Plan,
    dependency_waves,
    targets_from_frame,
    terminal_tasks,
    to_dict,
)
from devague.plan_convergence import dependency_blockers
from devague.plan_convergence import evaluate as evaluate_plan
from devague.render import deliverables_md, plan_md

PLANS_OUT_DIR = Path("docs/plans")

_JSON_HELP = "Emit structured JSON."
_TASK_ID_HELP = "Task id."
_INSTRUCTION_HELP = "Verbatim working instruction — how to verify or implement this task."
_RESOLVE_HINT = "resolve: "  # prefix for a "; "-joined blocker remediation hint

PLAN_MOVES = {
    "new": "Start a plan from a converged frame (derives coverage targets).",
    "task": "Add a task; optionally --accept / --dep / --covers / --instruction inline.",
    "instruct": "Add/update a task's working instruction (may flip confirmed -> proposed).",
    "accept": "Add an acceptance criterion to a task.",
    "amend": (
        "Edit a task's summary and/or replace/remove acceptance criteria by index "
        "(may flip confirmed -> proposed; refuses on a rejected task)."
    ),
    "depend": (
        "Record that a task depends on another (--on); --remove cuts one edge "
        "(may flip confirmed -> proposed)."
    ),
    "cover": "Mark a task as covering a coverage target (c*/h*).",
    "defer": (
        "Deliberately exclude a coverage target from this plan's gate "
        "(--reason TEXT), or --undo to reverse it."
    ),
    "confirm": "Confirm a task (user-only — no fabricated rigor).",
    "reject": "Reject a task.",
    "risk": (
        "Record a first-class plan risk instead of papering over it, "
        "or --resolve RID --decision TEXT to close one out."
    ),
    "converge": "Check whether the plan can export, against the live frame.",
    "export": "Write the buildable plan — only once the plan converges.",
    "waves": "Emit deterministic dependency waves (scheduling metadata, not orchestration).",
    "deliverables": (
        "Read-only preview of what exists once every task completes "
        "(renders even when not converged)."
    ),
    "status": "Report where the plan stands + the recommended next move (read-only).",
    "show": "Render the plan.",
    "list": "List plans.",
}

_STATUS_LABELS = StatusLabels(
    noun="plan",
    ready_key="ready_for_plan",
    export_move="devague plan export   # write the buildable plan",
    empty_text=(
        "no plans yet — seed one from a converged frame:\n"
        '  devague plan new --frame "<slug>"\n'
        "  (the frame must have converged in the /think skill first)"
    ),
)


# ── shared helpers ──────────────────────────────────────────────────────────
def _load_source_frame(slug: str) -> Frame:
    try:
        return store.load(slug)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"invalid source frame slug: {slug!r}",
            "the plan's frame_slug is corrupt",
        ) from exc
    except FileNotFoundError:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"source frame '{slug}' no longer exists",
            "the plan was built from a frame that has since been deleted",
        ) from None


def _merge_deferred_state(old_targets: list, new_targets: list) -> list:
    """Carry persisted per-target deferral state across a live-frame re-derive
    (issue #85).

    :func:`targets_from_frame` builds brand-new ``CoverageTarget`` instances from
    the frame every time — deriving them fresh is exactly what makes frame drift
    detectable — but that also means the freshly derived objects know nothing
    about deferral, which lives only on the plan's own record (``plan.targets``,
    persisted via ``plan_store``). Without this, every ``converge``/``export``/
    ``status`` call would silently drop a recorded deferral the moment it
    re-derives targets from the live frame. A deferred target the live re-derive
    no longer contains (the underlying claim was rejected, say) simply has
    nothing to carry forward — its deferral becomes moot, not resurrected as a
    phantom target.
    """
    deferred = {tg.id: (tg.deferred, tg.deferred_reason) for tg in old_targets if tg.deferred}
    for tg in new_targets:
        if tg.id in deferred:
            tg.deferred, tg.deferred_reason = deferred[tg.id]
    return new_targets


def _live(plan: Plan):
    """Re-load the source frame and re-derive targets; guard against frame drift.

    Re-derived targets are freshly built by :func:`targets_from_frame` and so
    start with no deferral state; :func:`_merge_deferred_state` carries the
    plan's persisted deferrals across the re-derive (issue #85) before returning.
    """
    frame = _load_source_frame(plan.frame_slug)
    fres = evaluate_frame(frame)
    if not fres.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"source frame '{frame.slug}' has regressed below convergence",
            f"re-converge the frame first: devague converge --frame {frame.slug}",
        )
    targets = _merge_deferred_state(plan.targets, targets_from_frame(frame))
    return frame, targets


def _live_frame_and_targets(plan: Plan):
    """Load the live source frame and re-derive targets — WITHOUT gating on the
    frame's own convergence (unlike :func:`_live`).

    ``deliverables`` is a read-only preview that must never refuse (#70, issue
    #20): even a frame that has regressed below its own convergence gate still
    has *some* confirmed announcement/after_state/success_signal claims worth
    showing, so this deliberately skips the ``evaluate_frame`` check that
    ``converge``/``export``/``status`` use to catch frame drift. A missing or
    corrupt source frame still raises via :func:`_load_source_frame` — there is
    no state to synthesize from at all, which is a different failure than "not
    converged yet."

    Like :func:`_live`, deferred state is carried across the re-derive (issue
    #85) — otherwise a previously deferred target would count as a fresh
    blocker here, making the ``converged`` bool this feeds disagree with what
    ``converge``/``status``/``export`` report for the exact same plan.
    """
    frame = _load_source_frame(plan.frame_slug)
    targets = _merge_deferred_state(plan.targets, targets_from_frame(frame))
    return frame, targets


def _require_task(plan: Plan, tid: str):
    task = plan.find_task(tid)
    if task is None:
        raise DevagueError(EXIT_USER_ERROR, f"no such task: {tid}", "run 'devague plan show'")
    return task


def _require_target(plan: Plan, target_id: str) -> None:
    """Validate ``target_id`` against the plan's coverage targets (issue #90).

    ``converge``/``status``/``export`` all re-derive targets from the **live**
    source frame via :func:`_live`, so when a frame legitimately grows a new
    confirmed claim/honesty condition mid-run, ``status`` immediately recommends
    covering that new id. Checking only the (possibly stale) *stored* snapshot
    here would make that exact recommended cover refuse as "unknown coverage
    target" — two moves disagreeing about the same id in the same breath, and a
    plan that grew could never converge again.

    So: the stored snapshot is checked first (the common, no-I/O case — nothing
    changed since the plan last converged). Only when ``target_id`` is absent
    there do we consult the live frame; a hit refreshes and persists ``plan.targets``
    so the stored copy catches up without a separate ``plan converge`` (the caller's
    own ``plan_store.save`` right after this call carries the refreshed snapshot).

    Decision (recorded as park v4 / plan risk r2): if the source frame has itself
    regressed below its own convergence gate, :func:`_live` raises — that error is
    let through here as-is rather than caught and reworded into "unknown coverage
    target". A target absent from the stored snapshot when the frame is unhealthy
    is genuinely unverifiable (it may be a real, newly-grown target that just
    hasn't been re-converged, or a plain typo — there is no way to tell from a
    frame that cannot currently be evaluated), so surfacing the real cause — "the
    frame has regressed, re-converge it first" — is more honest than silently
    blaming the target id for a problem that lives in the frame, not the plan.
    A target already known to the stored snapshot is unaffected by any of this:
    it never touches the live frame, so it keeps working through a frame
    regression exactly as it did before this fix.
    """
    if plan.find_target(target_id) is not None:
        return
    _frame, live_targets = _live(plan)  # raises as-is on a regressed source frame
    if not any(tg.id == target_id for tg in live_targets):
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown coverage target: {target_id}",
            "run 'devague plan show' to see targets (c*/h*)",
        )
    plan.targets = live_targets  # persist the refreshed snapshot on success


def _require_dep_target(
    plan: Plan, subject_id: str, dep_id: str, *, flag: str, self_hint: str
) -> None:
    """Validate a dependency edge at authoring time — a self-cycle or an unknown
    task id is refused the moment ``--dep``/``--on`` is given (issue #86),
    instead of surfacing only much later as a ``plan converge``/``plan waves``
    dependency-graph blocker, after the authoring context (which id was
    actually meant) is long gone. The reporter hit the self-cycle case twice in
    one session: the task id is assigned BY ``plan task``, so an author who
    predicts the next id wrongly in ``--dep`` records a task that depends on
    itself, invisible until ``plan waves`` reports a bare ``dependency cycle:
    tN -> tN``.

    Shared by both add paths: ``plan task --dep`` (``subject_id`` is the
    about-to-be-assigned id, predicted via ``Plan._next`` before the task
    exists) and ``plan depend <tN> --on <tM>``'s add path (``subject_id`` is
    the already-assigned ``<tN>``). Neither call site invokes this on the
    ``depend --remove`` path — removing an edge must keep working on an
    already-broken graph (a self-cycle or dangling dep recorded before this
    check existed, e.g. by an older devague or by hand-edited JSON), so a plan
    upgrading with pre-existing damage stays repairable.

    Deliberately narrow: a two-or-more-task cycle (a depends on b depends on
    a) is NOT caught here — both tasks already exist and neither equals the
    other, so this passes them through. That check already lives in
    :mod:`devague.plan_convergence` (``converge``/``waves``) and is left
    alone; this is creation-time feedback for the two mistakes a human can
    make in a single keystroke, not a replacement for the gate.
    """
    if dep_id == subject_id:
        raise DevagueError(EXIT_USER_ERROR, "task cannot depend on itself", self_hint)
    if plan.find_task(dep_id) is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown task: {dep_id}",
            f"{flag} {dep_id} does not match any existing task; "
            "run 'devague plan show' to see current tasks",
        )


# ── the re-confirm rule (#53 t5, sharpened in #53-esd t1) ────────────────────
# A demoting change — ``instruct``, ``amend``, ``depend --remove`` — alters something
# the user already confirmed, so it must go back through the user: setting/changing it
# on a CONFIRMED task flips the task back to 'proposed'. A task that is already
# 'proposed' or 'rejected' is unaffected by this rule; only its field(s) change.
_FLIP_SUFFIX = " (confirmed -> proposed; re-confirm)"


def _demote_if_confirmed(task) -> bool:
    flipped = task.status == "confirmed"
    if flipped:
        task.status = "proposed"
    return flipped


def _flip_suffix(flipped: bool) -> str:
    """The stdout-visible flip note (#53-esd t1, issue #67 hardening): a harness that
    reads only stdout must still see the confirmed -> proposed demotion, not just the
    stderr diagnostic."""
    return _FLIP_SUFFIX if flipped else ""


def _flip_diagnostic(task_id: str, what_changed: str) -> None:
    emit_diagnostic(
        f"note: {task_id} was confirmed; {what_changed} flips it back to 'proposed' — "
        f"re-confirm it (devague plan confirm {task_id})"
    )


# ── moves ───────────────────────────────────────────────────────────────────
def cmd_plan_new(args: argparse.Namespace) -> int:
    frame = resolve_frame(args.frame)
    result = evaluate_frame(frame)
    if not result.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"frame '{frame.slug}' has not converged; cannot start a plan",
            _RESOLVE_HINT + "; ".join(result.blockers),
        )
    if plan_store.path_for(frame.slug).exists():
        raise DevagueError(
            EXIT_USER_ERROR,
            f"a plan for frame '{frame.slug}' already exists",
            f"inspect it: devague plan show --plan {frame.slug}",
        )
    plan = Plan(
        slug=frame.slug,
        title=args.title or frame.title,
        frame_slug=frame.slug,
        targets=targets_from_frame(frame),
    )
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {"slug": plan.slug, "frame": plan.frame_slug, "targets": len(plan.targets)},
            json_mode=True,
        )
    else:
        emit_result(
            f"created plan '{plan.slug}' from frame '{frame.slug}' "
            f"({len(plan.targets)} coverage target(s))",
            json_mode=False,
        )
    return 0


def cmd_plan_task(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    for tid in args.covers or []:
        _require_target(plan, tid)
    # The task id is assigned BY this call (`add_task` below); validate every
    # `--dep` against the id it is *about* to receive, before creating anything
    # (issue #86) — mirrors how `--covers` is validated above, before mutation.
    next_id = Plan._next(plan.tasks, "t")
    for dep in args.dep or []:
        self_hint = f"--dep {dep} names the id this task will receive; depend on an existing task"
        _require_dep_target(plan, next_id, dep, flag="--dep", self_hint=self_hint)
    task = plan.add_task(args.summary, origin=args.origin)
    task.instruction = args.instruction or ""
    for crit in args.accept or []:
        plan.add_acceptance(task, crit)
    for dep in args.dep or []:
        plan.add_dep(task, dep)
    for tid in args.covers or []:
        plan.add_cover(task, tid)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": task.id,
                "status": task.status,
                "acceptance": len(task.acceptance_criteria),
                "deps": task.deps,
                "covers": task.covers,
                "instruction": task.instruction,
            },
            json_mode=True,
        )
    else:
        emit_result(f"added {task.id} ({task.status})", json_mode=False)
    return 0


def cmd_plan_instruct(args: argparse.Namespace) -> int:
    """Add/update a task's working instruction (verbatim; never fabricated).

    Re-confirm rule (#53 t5, gate-2 review): setting or changing the instruction on a
    CONFIRMED task flips it back to 'proposed' — the instruction is part of what the
    user confirmed, so a change to it must go back through the user. A task that is
    already 'proposed' (or 'rejected') is unaffected by this rule; only its instruction
    changes.
    """
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    task.instruction = args.text
    flipped = _demote_if_confirmed(task)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": task.id,
                "instruction": task.instruction,
                "status": task.status,
                "flipped": flipped,
            },
            json_mode=True,
        )
    else:
        emit_result(f"{task.id}: instruction set{_flip_suffix(flipped)}", json_mode=False)
    if flipped:
        _flip_diagnostic(task.id, "changing its instruction")
    return 0


def cmd_plan_accept(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    plan.add_acceptance(task, args.text)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": task.id, "acceptance": len(task.acceptance_criteria)}, json_mode=True)
    else:
        emit_result(f"{task.id}: +acceptance criterion", json_mode=False)
    return 0


def cmd_plan_amend(args: argparse.Namespace) -> int:
    """``amend`` — edit a task's summary and/or replace/remove acceptance criteria
    by index (#53-esd t1, issue #68's task-recreation escape hatch).

    Scoped to summary + acceptance criteria only — deps/covers/instruction each
    already have their own move (``depend``/``cover``/``instruct``). Re-confirm rule:
    amending a CONFIRMED task flips it back to 'proposed' (same rule as ``instruct``
    and ``depend --remove``). Design decision (deliberately stricter than
    ``instruct``): amend REFUSES outright on a REJECTED task — silently letting a
    rejected task's declared work keep changing would make 'rejected' meaningless;
    the honest move is a new task, not a resurrection through the back door.
    """
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    if task.status == "rejected":
        raise DevagueError(
            EXIT_USER_ERROR,
            f"{task.id} is rejected; amend refuses to edit a rejected task",
            "add a new task instead — a rejected task's content should not change",
        )
    if args.summary is None and not args.accept_replace and not args.accept_remove:
        raise DevagueError(
            EXIT_USER_ERROR,
            "nothing to amend",
            'pass --summary "<text>", --accept-replace <n> "<text>", ' "and/or --accept-remove <n>",
        )
    try:
        accept_replace = [(int(n), text) for n, text in (args.accept_replace or [])]
        accept_remove = [int(n) for n in (args.accept_remove or [])]
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"acceptance criterion index must be an integer: {exc}",
            'e.g. --accept-replace 1 "new text" / --accept-remove 2',
        ) from exc
    try:
        plan.amend_task(
            task, summary=args.summary, accept_replace=accept_replace, accept_remove=accept_remove
        )
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR, str(exc), "run 'devague plan show' to see current criteria"
        ) from exc
    flipped = _demote_if_confirmed(task)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": task.id,
                "summary": task.summary,
                "acceptance_criteria": list(task.acceptance_criteria),
                "status": task.status,
                "flipped": flipped,
            },
            json_mode=True,
        )
    else:
        emit_result(f"{task.id}: amended{_flip_suffix(flipped)}", json_mode=False)
    if flipped:
        _flip_diagnostic(task.id, "amending it")
    return 0


def cmd_plan_depend(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    if args.remove:
        return _cmd_plan_depend_remove(args, plan, task)
    _require_dep_target(
        plan,
        args.id,
        args.on,
        flag="--on",
        self_hint=f"--on {args.on} is the same task; depend on a different, existing task",
    )
    plan.add_dep(task, args.on)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": task.id, "deps": task.deps}, json_mode=True)
    else:
        emit_result(f"{task.id} depends on {args.on}", json_mode=False)
    return 0


def _cmd_plan_depend_remove(args: argparse.Namespace, plan: Plan, task) -> int:
    """``depend <tN> --on <tM> --remove`` — cut exactly one edge (#53-esd t1, issue #68).

    Everything else on the task (summary, acceptance criteria, covers, instruction)
    stays untouched; only ``deps`` and — if the task was confirmed — ``status`` change.
    """
    removed = plan.remove_dep(task, args.on)
    if not removed:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"{task.id} does not depend on {args.on}",
            "run 'devague plan show' to see its current deps",
        )
    flipped = _demote_if_confirmed(task)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {"id": task.id, "deps": task.deps, "status": task.status, "flipped": flipped},
            json_mode=True,
        )
    else:
        emit_result(
            f"{task.id} no longer depends on {args.on}{_flip_suffix(flipped)}", json_mode=False
        )
    if flipped:
        _flip_diagnostic(task.id, f"removing its dependency on {args.on}")
    return 0


def cmd_plan_cover(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    _require_target(plan, args.target)
    plan.add_cover(task, args.target)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": task.id, "covers": task.covers}, json_mode=True)
    else:
        emit_result(f"{task.id} covers {args.target}", json_mode=False)
    return 0


def cmd_plan_defer(args: argparse.Namespace) -> int:
    """``plan defer <target-id> --reason "<text>"`` — deliberately exclude a
    coverage target from this plan's gate, or ``--undo`` to reverse a prior
    deferral (issue #85: a milestone-scoped plan should not have to fake
    coverage of a target that genuinely belongs to a later plan just to make
    the gate go green).

    Mirrors ``plan risk --resolve``'s shape and house style: the target is
    validated the same way ``cover`` validates one (:func:`_require_target` —
    stored snapshot first, live frame fallback, refreshing the persisted
    snapshot on a live hit), and the create/undo paths share one subcommand the
    way risk's create/resolve paths do.
    """
    plan = resolve_plan(args.plan)
    _require_target(plan, args.id)  # may refresh + persist plan.targets in-memory
    if args.undo:
        return _cmd_plan_defer_undo(args, plan)
    if not args.reason:
        raise DevagueError(
            EXIT_USER_ERROR,
            "--reason is required to defer a coverage target",
            f'pass --reason "<why this is out of scope>", '
            f"or --undo to reverse a prior defer for {args.id}",
        )
    try:
        target = plan.defer_target(args.id, args.reason)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR, str(exc), "run 'devague plan show' to see current targets"
        ) from exc
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {"id": target.id, "deferred": target.deferred, "reason": target.deferred_reason},
            json_mode=True,
        )
    else:
        emit_result(f"{target.id} -> deferred ({target.deferred_reason})", json_mode=False)
    return 0


def _cmd_plan_defer_undo(args: argparse.Namespace, plan: Plan) -> int:
    """``plan defer <target-id> --undo`` — reverse a prior deferral, returning
    the target to the active coverage gate."""
    try:
        target = plan.undefer_target(args.id)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR, str(exc), "run 'devague plan show' to see current targets"
        ) from exc
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": target.id, "deferred": target.deferred}, json_mode=True)
    else:
        emit_result(f"{target.id} -> no longer deferred", json_mode=False)
    return 0


def _transition(args: argparse.Namespace, status: str) -> int:
    """Transactional multi-id confirm/reject (issue #86): every id is validated
    against the plan FIRST; if any is unknown, nothing is changed and the
    message names the offender(s) — matching the frame-side contract
    (``confirm.py`` ``_run``, issue #17). Plan tasks have no honesty
    conditions / hard questions to cascade over (that is a frame-only
    concept), so unlike the frame side there is nothing to cascade — only the
    output shape (one ``"{id} -> {status}"`` line per id) mirrors it.
    Single-id usage (still the common case) behaves exactly as before.
    """
    plan = resolve_plan(args.plan)
    ids = list(args.ids)
    unknown = [tid for tid in ids if plan.find_task(tid) is None]
    if unknown:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such task: {', '.join(unknown)}",
            "run 'devague plan show'; the batch is transactional — nothing was changed",
        )
    for tid in ids:
        plan.set_status(tid, status)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"ids": ids, "status": status}, json_mode=True)
    else:
        emit_result("\n".join(f"{tid} -> {status}" for tid in ids), json_mode=False)
    return 0


def cmd_plan_confirm(args: argparse.Namespace) -> int:
    return _transition(args, "confirmed")


def cmd_plan_reject(args: argparse.Namespace) -> int:
    return _transition(args, "rejected")


def cmd_plan_risk(args: argparse.Namespace) -> int:
    """Record a new plan risk, or (``--resolve RID --decision TEXT``) close one
    out — mirrors ``park --resolve`` (t5) on the risk subcommand.

    ``--kind`` is optional at the parser level (so a bare ``--resolve`` call
    does not need it), but the create path still requires it — refused here,
    in the handler, rather than by argparse. The create path (positional text
    + ``--kind`` + optional ``--task``) is otherwise unchanged.
    """
    plan = resolve_plan(args.plan)
    if args.resolve:
        return _cmd_plan_risk_resolve(args, plan)
    if not args.text or not args.kind:
        raise DevagueError(
            EXIT_USER_ERROR,
            "text and --kind are required to record a new risk",
            'pass "<risk text>" --kind <kind>, or --resolve RID --decision "<text>" to '
            "resolve an existing risk",
        )
    if args.task is not None:
        _require_task(plan, args.task)
    risk = plan.add_risk(args.text, args.kind, task_id=args.task)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": risk.id, "kind": risk.kind, "task": risk.task_id}, json_mode=True)
    else:
        emit_result(f"recorded risk {risk.id} ({risk.kind})", json_mode=False)
    return 0


def _cmd_plan_risk_resolve(args: argparse.Namespace, plan: Plan) -> int:
    """``plan risk --resolve RID --decision TEXT`` — close out a risk without
    routing it through confirm/reject (the plan-side twin of ``park --resolve``, t5).

    Fail-closed, same contract as :meth:`Plan.resolve_risk`: a bare ``--resolve``
    without ``--decision`` persists nothing; an unknown id is refused; an
    already-resolved id is refused rather than silently no-op'd.
    """
    if not args.decision:
        raise DevagueError(
            EXIT_USER_ERROR,
            "--decision is required to resolve a risk",
            f'pass --decision "<text>" describing the resolution for {args.resolve}',
        )
    try:
        risk = plan.resolve_risk(args.resolve, args.decision)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR, str(exc), "run 'devague plan show' to see current risks"
        ) from exc
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {"id": risk.id, "resolved": risk.resolved, "resolution": risk.resolution},
            json_mode=True,
        )
    else:
        emit_result(f"{risk.id} -> resolved ({risk.resolution})", json_mode=False)
    return 0


def cmd_plan_converge(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    _frame, targets = _live(plan)
    plan.targets = targets  # refresh the snapshot from the live frame
    result = evaluate_plan(plan, targets=targets)
    if result.ready and plan.status == "drafting":
        plan.status = "converged"
    elif not result.ready and plan.status == "converged":
        plan.status = "drafting"
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result(
            {
                "ready_for_plan": result.ready,
                "blockers": result.blockers,
                "warnings": result.warnings,
                "parked_items": result.parked_items,
                "required_next_moves": result.required_next_moves,
            },
            json_mode=True,
        )
    elif result.ready:
        msg = "converged ✓"
        if result.warnings:
            msg += "\nwarnings:\n" + "\n".join(f"  - {w}" for w in result.warnings)
        emit_result(msg, json_mode=False)
    else:
        msg = "not converged:\n" + "\n".join(f"  - {b}" for b in result.blockers)
        if result.warnings:
            msg += "\nwarnings:\n" + "\n".join(f"  - {w}" for w in result.warnings)
        emit_result(msg, json_mode=False)
    return 0


def cmd_plan_export(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    frame, targets = _live(plan)
    plan.targets = targets
    result = evaluate_plan(plan, targets=targets)
    if not result.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            "plan has not converged; cannot export",
            _RESOLVE_HINT + "; ".join(result.blockers),
        )
    plan.status = "exported"
    text = plan_md.render_plan(plan, frame)
    PLANS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PLANS_OUT_DIR / dated_name(plan.created, plan.slug)
    out_path.write_text(text, encoding="utf-8")
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"path": str(out_path), "format": args.format}, json_mode=True)
    else:
        emit_result(f"exported plan to {out_path}", json_mode=False)
    return 0


def cmd_plan_waves(args: argparse.Namespace) -> int:
    """Emit the plan's dependency waves — deterministic scheduling metadata only.

    Read-only and convergence-agnostic: waves derive purely from the task dependency
    graph, so they work on an in-progress plan. Devague describes the graph; an
    external operator (Culture, codexd, …) decides how to execute it — see #20. A cycle
    or a dep on a missing/rejected task is refused by reusing the plan-convergence
    integrity blockers.
    """
    plan = resolve_plan(args.plan)
    blockers = dependency_blockers(plan)
    if blockers:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot derive waves: the dependency graph is not sound",
            _RESOLVE_HINT + "; ".join(blockers),
        )
    waves = dependency_waves(plan.tasks)
    if getattr(args, "json", False):
        # Enough for a subagent brief with no external context (#53 t9, c8/h12):
        # every active (non-rejected) task appearing in ``waves`` gets its full
        # working contract — summary, verbatim instruction, acceptance criteria,
        # and covered targets — keyed by task id.
        tasks_payload = {
            t.id: {
                "summary": t.summary,
                "instruction": t.instruction,
                "acceptance_criteria": list(t.acceptance_criteria),
                "covers": list(t.covers),
            }
            for t in plan.tasks
            if t.status != "rejected"
        }
        emit_result({"plan": plan.slug, "waves": waves, "tasks": tasks_payload}, json_mode=True)
    elif not waves:
        emit_result("no tasks to schedule", json_mode=False)
    else:
        lines = [f"wave {i}: {', '.join(w)}" for i, w in enumerate(waves)]
        emit_result("\n".join(lines), json_mode=False)
    return 0


def _confirmed_texts(frame: Frame, kind: str) -> list[str]:
    return [c.text for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _open_items_payload(frame: Frame, plan: Plan) -> list[dict]:
    items = [
        {"kind": v.kind, "text": v.text}
        for v in frame.open_vagueness
        if v.kind != "unknown_blocking"
    ]
    items += [{"kind": r.kind, "text": r.text} for r in plan.risks if r.kind != "unknown_blocking"]
    return items


def cmd_plan_deliverables(args: argparse.Namespace) -> int:
    """The read-only "what do we have in the end?" view (issue #70).

    Synthesizes from the live frame + plan state only — the frame's confirmed
    ``announcement`` / ``after_state`` / ``success_signal`` claims (verbatim), the
    plan's terminal tasks (active tasks no other active task depends on) with their
    acceptance criteria, and surviving open items (the frame's non-blocking parked
    vagueness plus the plan's non-blocking risks). Evaluates the plan gate read-only
    — like ``status`` — but never persists the drafting/converged transition, and
    unlike every gated move it never refuses on a not-converged plan: it renders an
    explicit banner instead (#20). Never writes to ``.devague/`` at all.
    """
    plan = resolve_plan(args.plan)
    frame, targets = _live_frame_and_targets(plan)
    result = evaluate_plan(plan, targets=targets)
    terminal = terminal_tasks(plan.tasks)
    if getattr(args, "json", False):
        emit_result(
            {
                "plan": plan.slug,
                "converged": result.ready,
                "announcement": _confirmed_texts(frame, "announcement"),
                "after_state": _confirmed_texts(frame, "after_state"),
                "success_signal": _confirmed_texts(frame, "success_signal"),
                "terminal_tasks": [
                    {
                        "id": t.id,
                        "summary": t.summary,
                        "acceptance_criteria": list(t.acceptance_criteria),
                    }
                    for t in terminal
                ],
                "open_items": _open_items_payload(frame, plan),
            },
            json_mode=True,
        )
    else:
        emit_result(
            deliverables_md.render_deliverables(plan, frame, converged=result.ready),
            json_mode=False,
        )
    return 0


def cmd_plan_status(args: argparse.Namespace) -> int:
    """Where the plan stands + the recommended next move — read-only.

    Re-evaluates against the **live** source frame (like ``converge``/``export``),
    so frame drift surfaces as a real error on stderr before any stdout. Internalised
    from the ``spec-to-plan`` skill wrapper (issue #30); unlike ``converge`` it never
    persists the ``drafting``↔``converged`` transition.
    """
    json_mode = getattr(args, "json", False)
    slugs = plan_store.list_slugs()
    if not slugs:
        emit_empty(_STATUS_LABELS, json_mode=json_mode)
    else:
        # resolve_plan + _live raise here (before any stdout) on a bad --plan or a
        # source frame that regressed below convergence — routed to stderr.
        plan = resolve_plan(args.plan)
        _frame, targets = _live(plan)
        plan.targets = targets  # in-memory refresh only; status does not save
        result = evaluate_plan(plan, targets=targets)
        emit_status(
            _STATUS_LABELS, selected=plan.slug, total=len(slugs), result=result, json_mode=json_mode
        )
    return 0


def cmd_plan_show(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    if getattr(args, "json", False):
        emit_result(to_dict(plan), json_mode=True)
    else:
        # Render needs the source frame for context; degrade gracefully if it's gone.
        try:
            frame = store.load(plan.frame_slug)
        except (FileNotFoundError, ValueError):
            frame = None
        emit_result(plan_md.render_plan(plan, frame), json_mode=False)
    return 0


def cmd_plan_list(args: argparse.Namespace) -> int:
    slugs = plan_store.list_slugs()
    current = plan_store.current_slug()
    if getattr(args, "json", False):
        emit_result({"plans": slugs, "current": current}, json_mode=True)
    elif not slugs:
        emit_result("no plans yet", json_mode=False)
    else:
        emit_result("\n".join(("* " if s == current else "  ") + s for s in slugs), json_mode=False)
    return 0


def cmd_plan_learn(args: argparse.Namespace) -> int:
    text = (
        "devague plan turns a converged spec into a buildable plan — the forward leg\n"
        "after working backwards into a spec. Seed a plan from a converged frame, then\n"
        "add tasks that collectively cover every coverage target (the frame's confirmed\n"
        "claims and honesty conditions). Each task earns acceptance criteria and an\n"
        "honest dependency order; genuine unknowns are parked as first-class risks.\n\n"
        "LLM-proposed tasks stay 'proposed' until the user confirms them — same\n"
        "anti-fabrication rule as claims. A plan exports only once it converges:\n"
        "every target covered by a confirmed task, every confirmed task has acceptance\n"
        "criteria, the dependency graph is acyclic, and no blocking risk remains.\n\n"
        "Moves:\n"
        + "\n".join(f"  {name:<9} {desc}" for name, desc in PLAN_MOVES.items())
        + "\n\nTo author the six operator skills (scope / think / spec-to-plan / "
        "assign-to-workforce /\ndeviate / summarize-delivery) in your own runtime, "
        "run 'devague learn skills'\n(with user consent)."
    )
    if getattr(args, "json", False):
        emit_result(
            {"tool": "devague plan", "moves": list(PLAN_MOVES), "summary": text}, json_mode=True
        )
    else:
        emit_result(text, json_mode=False)
    return 0


def cmd_plan_explain(args: argparse.Namespace) -> int:
    desc = PLAN_MOVES.get(args.move)
    if desc is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown plan move: {args.move}",
            "moves: " + ", ".join(PLAN_MOVES),
        )
    if getattr(args, "json", False):
        emit_result({"move": args.move, "description": desc}, json_mode=True)
    else:
        emit_result(f"{args.move}: {desc}", json_mode=False)
    return 0


def _cmd_plan_help(args: argparse.Namespace) -> int:
    args._plan_parser.print_help()
    return 0


# ── registration ─────────────────────────────────────────────────────────────
def _plan_opt(p: argparse.ArgumentParser) -> None:
    p.add_argument("--plan", help="Plan slug (default: current).")
    p.add_argument("--json", action="store_true", help=_JSON_HELP)


def register(sub: argparse._SubParsersAction) -> None:
    # Lazy import keeps the chassis' deferred-import discipline (avoids a cycle).
    from devague.cli import _DevagueArgumentParser

    p = sub.add_parser(
        "plan", help="Turn a converged spec into a buildable plan (the plan engine)."
    )
    psub = p.add_subparsers(dest="plan_command", parser_class=_DevagueArgumentParser)

    pn = psub.add_parser("new", help="Start a plan from a converged frame.")
    pn.add_argument("--frame", help="Source frame slug (default: current).")
    pn.add_argument("--title", help="Plan title (defaults to the frame title).")
    pn.add_argument("--json", action="store_true", help=_JSON_HELP)
    pn.set_defaults(func=cmd_plan_new)

    pt = psub.add_parser("task", help="Add a task.")
    pt.add_argument("summary", help="What the task delivers.")
    pt.add_argument("--accept", action="append", help="An acceptance criterion (repeatable).")
    pt.add_argument("--dep", action="append", help="A task id this depends on (repeatable).")
    pt.add_argument("--covers", action="append", help="A coverage target id c*/h* (repeatable).")
    pt.add_argument("--origin", choices=("user", "llm"), default="user", help="Who proposed it.")
    pt.add_argument("--instruction", default="", help=_INSTRUCTION_HELP)
    _plan_opt(pt)
    pt.set_defaults(func=cmd_plan_task)

    pin = psub.add_parser("instruct", help="Add/update a task's working instruction.")
    pin.add_argument("id", help=_TASK_ID_HELP)
    pin.add_argument("text", help=_INSTRUCTION_HELP)
    _plan_opt(pin)
    pin.set_defaults(func=cmd_plan_instruct)

    pa = psub.add_parser("accept", help="Add an acceptance criterion to a task.")
    pa.add_argument("id", help="Task id (e.g. t1).")
    pa.add_argument("text", help="The acceptance criterion.")
    _plan_opt(pa)
    pa.set_defaults(func=cmd_plan_accept)

    pam = psub.add_parser(
        "amend", help="Edit a task's summary and/or replace/remove acceptance criteria by index."
    )
    pam.add_argument("id", help=_TASK_ID_HELP)
    pam.add_argument("--summary", help="Replace the task summary verbatim.")
    pam.add_argument(
        "--accept-replace",
        nargs=2,
        action="append",
        metavar=("N", "TEXT"),
        help="Replace the Nth (1-indexed) acceptance criterion with TEXT (repeatable).",
    )
    pam.add_argument(
        "--accept-remove",
        action="append",
        metavar="N",
        help="Remove the Nth (1-indexed) acceptance criterion (repeatable).",
    )
    _plan_opt(pam)
    pam.set_defaults(func=cmd_plan_amend)

    pd = psub.add_parser("depend", help="Record that a task depends on another (or --remove).")
    pd.add_argument("id", help="The dependent task id.")
    pd.add_argument("--on", required=True, help="The task id it depends on.")
    pd.add_argument(
        "--remove", action="store_true", help="Remove this dependency edge instead of adding it."
    )
    _plan_opt(pd)
    pd.set_defaults(func=cmd_plan_depend)

    pc = psub.add_parser("cover", help="Mark a task as covering a coverage target.")
    pc.add_argument("id", help=_TASK_ID_HELP)
    pc.add_argument("--target", required=True, help="Coverage target id (c*/h*).")
    _plan_opt(pc)
    pc.set_defaults(func=cmd_plan_cover)

    pdf = psub.add_parser(
        "defer", help="Deliberately exclude a coverage target from this plan's gate."
    )
    pdf.add_argument("id", help="Coverage target id (c*/h*).")
    pdf.add_argument("--reason", help="Why this target is out of scope for this plan.")
    pdf.add_argument(
        "--undo", action="store_true", help="Reverse a prior defer instead of creating one."
    )
    _plan_opt(pdf)
    pdf.set_defaults(func=cmd_plan_defer)

    pcf = psub.add_parser("confirm", help="Confirm one or more tasks (user-only).")
    pcf.add_argument("ids", nargs="+", help="One or more task ids (e.g. t1 t2 t3).")
    _plan_opt(pcf)
    pcf.set_defaults(func=cmd_plan_confirm)

    prj = psub.add_parser("reject", help="Reject one or more tasks.")
    prj.add_argument("ids", nargs="+", help="One or more task ids (e.g. t1 t2 t3).")
    _plan_opt(prj)
    prj.set_defaults(func=cmd_plan_reject)

    prk = psub.add_parser("risk", help="Record or resolve a first-class plan risk.")
    prk.add_argument("text", nargs="?", help="The risk (required unless --resolve).")
    prk.add_argument("--kind", choices=RISK_KINDS, help="Risk kind (required unless --resolve).")
    prk.add_argument("--task", help="Task id this risk attaches to (optional).")
    prk.add_argument(
        "--resolve", metavar="RID", help="Resolve an existing risk id instead of creating one."
    )
    prk.add_argument("--decision", help="The resolution text recorded with --resolve.")
    _plan_opt(prk)
    prk.set_defaults(func=cmd_plan_risk)

    pcv = psub.add_parser("converge", help="Check whether the plan can export.")
    _plan_opt(pcv)
    pcv.set_defaults(func=cmd_plan_converge)

    pex = psub.add_parser("export", help="Export the buildable plan (requires convergence).")
    pex.add_argument("--format", default="plan-md", choices=("plan-md",), help="Renderer format.")
    _plan_opt(pex)
    pex.set_defaults(func=cmd_plan_export)

    pwv = psub.add_parser("waves", help="Emit deterministic dependency waves (metadata only).")
    _plan_opt(pwv)
    pwv.set_defaults(func=cmd_plan_waves)

    pdl = psub.add_parser(
        "deliverables", help="Preview what exists once every task completes (read-only)."
    )
    _plan_opt(pdl)
    pdl.set_defaults(func=cmd_plan_deliverables)

    pst = psub.add_parser("status", help="Where the plan stands + the recommended next move.")
    _plan_opt(pst)
    pst.set_defaults(func=cmd_plan_status)

    psh = psub.add_parser("show", help="Render the plan.")
    _plan_opt(psh)
    psh.set_defaults(func=cmd_plan_show)

    pls = psub.add_parser("list", help="List plans.")
    pls.add_argument("--json", action="store_true", help=_JSON_HELP)
    pls.set_defaults(func=cmd_plan_list)

    pln = psub.add_parser("learn", help="Teach the spec-to-plan method.")
    pln.add_argument("--json", action="store_true", help=_JSON_HELP)
    pln.set_defaults(func=cmd_plan_learn)

    pxp = psub.add_parser("explain", help="Explain one plan move.")
    pxp.add_argument("move", help="A plan move name.")
    pxp.add_argument("--json", action="store_true", help=_JSON_HELP)
    pxp.set_defaults(func=cmd_plan_explain)

    p.set_defaults(func=_cmd_plan_help, _plan_parser=p)
