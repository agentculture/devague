"""``specifix whoami`` — placeholder verb.

See :mod:`specifix.cli._commands.learn` for why the verbs are stubs.
``whoami`` will eventually be the smallest identity / auth probe; today it
prints an honest "not yet implemented" line.
"""

from __future__ import annotations

import argparse

from specifix import __version__
from specifix.cli._output import emit_result

_TEXT = "specifix — not yet implemented; specifix is greenfield. See CLAUDE.md."


def _json_payload() -> dict[str, object]:
    return {
        "tool": "specifix",
        "version": __version__,
        "status": "greenfield",
        "verb": "whoami",
        "message": _TEXT,
    }


def cmd_whoami(args: argparse.Namespace) -> int:
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(_json_payload(), json_mode=True)
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("whoami", help="Print specifix's identity probe (stub).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_whoami)
