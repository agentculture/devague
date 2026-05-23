"""``devague question`` — record/list/resolve pending user decisions.

Durable, uncommitted working state under .devague/questions/<slug>.md. The CLI
owns the format (decision c20). Nothing here auto-resolves: ``--resolve`` only
records a decision a human made; applying it into the frame is a separate,
explicit move (see the file header). Issue #14/#17.
"""

from __future__ import annotations

import argparse

from devague import questions_io, store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic, emit_result


def _load(slug: str) -> list[dict]:
    path = store.questions_path(slug)
    return questions_io.parse(path.read_text(encoding="utf-8")) if path.exists() else []


def _resolve_question(args: argparse.Namespace, slug: str, items: list[dict]) -> None:
    target = next((i for i in items if i["id"] == args.resolve), None)
    if target is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such question: {args.resolve}",
            "run 'devague question --list'",
        )
    target["resolved"] = True
    target["decision"] = args.decision
    store.write_questions(slug, questions_io.render(slug, items))
    if args.json:
        emit_result({"id": args.resolve, "resolved": True}, json_mode=True)
    else:
        emit_result(f"{args.resolve} -> resolved", json_mode=False)


def _add_question(args: argparse.Namespace, slug: str, items: list[dict]) -> None:
    new_id = questions_io.next_id(items)
    items.append({"id": new_id, "text": args.text, "resolved": False, "decision": None})
    path = store.write_questions(slug, questions_io.render(slug, items))
    if args.json:
        emit_result({"id": new_id, "text": args.text, "path": str(path)}, json_mode=True)
    else:
        emit_result(f"recorded {new_id}", json_mode=False)
        emit_diagnostic(f"wrote pending decision to {path} (uncommitted working state)")


def _list_questions(args: argparse.Namespace, slug: str, items: list[dict]) -> None:
    if args.json:
        emit_result({"slug": slug, "questions": items}, json_mode=True)
    else:
        emit_result(questions_io.render(slug, items), json_mode=False)


def cmd_question(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)  # validates the frame exists; never mutates it
    slug = frame.slug
    items = _load(slug)
    if args.resolve:
        _resolve_question(args, slug, items)
    elif args.text:
        _add_question(args, slug, items)
    else:  # default / --list: show the pending-decisions state
        _list_questions(args, slug, items)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("question", help="Record / list / resolve pending user decisions.")
    p.add_argument("text", nargs="?", help="Question text to record (omit to list).")
    p.add_argument("--resolve", metavar="QID", help="Mark a question id resolved.")
    p.add_argument("--decision", help="The decision note recorded with --resolve.")
    p.add_argument("--list", action="store_true", help="List pending decisions (default).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_question)
