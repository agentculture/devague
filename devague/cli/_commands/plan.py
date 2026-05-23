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
from devague.cli._output import emit_result
from devague.cli._plans import resolve_plan
from devague.convergence import evaluate as evaluate_frame
from devague.frame import Frame
from devague.plan import RISK_KINDS, Plan, targets_from_frame, to_dict
from devague.plan_convergence import evaluate as evaluate_plan
from devague.render import plan_md

PLANS_OUT_DIR = Path("docs/plans")

_JSON_HELP = "Emit structured JSON."
_TASK_ID_HELP = "Task id."

PLAN_MOVES = {
    "new": "Start a plan from a converged frame (derives coverage targets).",
    "task": "Add a task; optionally --accept / --dep / --covers inline.",
    "accept": "Add an acceptance criterion to a task.",
    "depend": "Record that a task depends on another (--on).",
    "cover": "Mark a task as covering a coverage target (c*/h*).",
    "confirm": "Confirm a task (user-only — no fabricated rigor).",
    "reject": "Reject a task.",
    "risk": "Record a first-class plan risk instead of papering over it.",
    "converge": "Check whether the plan can export, against the live frame.",
    "export": "Write the buildable plan — only once the plan converges.",
    "show": "Render the plan.",
    "list": "List plans.",
}


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


def _live(plan: Plan):
    """Re-load the source frame and re-derive targets; guard against frame drift."""
    frame = _load_source_frame(plan.frame_slug)
    fres = evaluate_frame(frame)
    if not fres.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"source frame '{frame.slug}' has regressed below convergence",
            f"re-converge the frame first: devague converge --frame {frame.slug}",
        )
    return frame, targets_from_frame(frame)


def _require_task(plan: Plan, tid: str):
    task = plan.find_task(tid)
    if task is None:
        raise DevagueError(EXIT_USER_ERROR, f"no such task: {tid}", "run 'devague plan show'")
    return task


def _require_target(plan: Plan, target_id: str) -> None:
    if plan.find_target(target_id) is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown coverage target: {target_id}",
            "run 'devague plan show' to see targets (c*/h*)",
        )


# ── moves ───────────────────────────────────────────────────────────────────
def cmd_plan_new(args: argparse.Namespace) -> int:
    frame = resolve_frame(args.frame)
    result = evaluate_frame(frame)
    if not result.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"frame '{frame.slug}' has not converged; cannot start a plan",
            "resolve: " + "; ".join(result.blockers),
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
    task = plan.add_task(args.summary, origin=args.origin)
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
            },
            json_mode=True,
        )
    else:
        emit_result(f"added {task.id} ({task.status})", json_mode=False)
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


def cmd_plan_depend(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    task = _require_task(plan, args.id)
    plan.add_dep(task, args.on)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": task.id, "deps": task.deps}, json_mode=True)
    else:
        emit_result(f"{task.id} depends on {args.on}", json_mode=False)
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


def _transition(args: argparse.Namespace, status: str) -> int:
    plan = resolve_plan(args.plan)
    if not plan.set_status(args.id, status):
        raise DevagueError(EXIT_USER_ERROR, f"no such task: {args.id}", "run 'devague plan show'")
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": args.id, "status": status}, json_mode=True)
    else:
        emit_result(f"{args.id} -> {status}", json_mode=False)
    return 0


def cmd_plan_confirm(args: argparse.Namespace) -> int:
    return _transition(args, "confirmed")


def cmd_plan_reject(args: argparse.Namespace) -> int:
    return _transition(args, "rejected")


def cmd_plan_risk(args: argparse.Namespace) -> int:
    plan = resolve_plan(args.plan)
    if args.task is not None:
        _require_task(plan, args.task)
    risk = plan.add_risk(args.text, args.kind, task_id=args.task)
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"id": risk.id, "kind": risk.kind, "task": risk.task_id}, json_mode=True)
    else:
        emit_result(f"recorded risk {risk.id} ({risk.kind})", json_mode=False)
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
        emit_result("converged ✓", json_mode=False)
    else:
        lines = "\n".join(f"  - {b}" for b in result.blockers)
        emit_result("not converged:\n" + lines, json_mode=False)
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
            "resolve: " + "; ".join(result.blockers),
        )
    plan.status = "exported"
    text = plan_md.render_plan(plan, frame)
    PLANS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PLANS_OUT_DIR / f"{plan.slug}.md"
    out_path.write_text(text, encoding="utf-8")
    plan_store.save(plan)
    if getattr(args, "json", False):
        emit_result({"path": str(out_path), "format": args.format}, json_mode=True)
    else:
        emit_result(f"exported plan to {out_path}", json_mode=False)
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
        "Moves:\n" + "\n".join(f"  {name:<9} {desc}" for name, desc in PLAN_MOVES.items())
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
    _plan_opt(pt)
    pt.set_defaults(func=cmd_plan_task)

    pa = psub.add_parser("accept", help="Add an acceptance criterion to a task.")
    pa.add_argument("id", help="Task id (e.g. t1).")
    pa.add_argument("text", help="The acceptance criterion.")
    _plan_opt(pa)
    pa.set_defaults(func=cmd_plan_accept)

    pd = psub.add_parser("depend", help="Record that a task depends on another.")
    pd.add_argument("id", help="The dependent task id.")
    pd.add_argument("--on", required=True, help="The task id it depends on.")
    _plan_opt(pd)
    pd.set_defaults(func=cmd_plan_depend)

    pc = psub.add_parser("cover", help="Mark a task as covering a coverage target.")
    pc.add_argument("id", help=_TASK_ID_HELP)
    pc.add_argument("--target", required=True, help="Coverage target id (c*/h*).")
    _plan_opt(pc)
    pc.set_defaults(func=cmd_plan_cover)

    pcf = psub.add_parser("confirm", help="Confirm a task (user-only).")
    pcf.add_argument("id", help=_TASK_ID_HELP)
    _plan_opt(pcf)
    pcf.set_defaults(func=cmd_plan_confirm)

    prj = psub.add_parser("reject", help="Reject a task.")
    prj.add_argument("id", help=_TASK_ID_HELP)
    _plan_opt(prj)
    prj.set_defaults(func=cmd_plan_reject)

    prk = psub.add_parser("risk", help="Record a first-class plan risk.")
    prk.add_argument("text", help="The risk.")
    prk.add_argument("--kind", required=True, choices=RISK_KINDS, help="Risk kind.")
    prk.add_argument("--task", help="Task id this risk attaches to (optional).")
    _plan_opt(prk)
    prk.set_defaults(func=cmd_plan_risk)

    pcv = psub.add_parser("converge", help="Check whether the plan can export.")
    _plan_opt(pcv)
    pcv.set_defaults(func=cmd_plan_converge)

    pex = psub.add_parser("export", help="Export the buildable plan (requires convergence).")
    pex.add_argument("--format", default="plan-md", choices=("plan-md",), help="Renderer format.")
    _plan_opt(pex)
    pex.set_defaults(func=cmd_plan_export)

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
