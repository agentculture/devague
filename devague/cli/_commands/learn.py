"""``devague learn`` — teach the working-backwards method and the moves."""

from __future__ import annotations

import argparse

from devague import __version__
from devague.cli._output import emit_result

MOVES = {
    "new": "Start a frame from the announcement (pretend it shipped).",
    "capture": "Record and classify a claim (audience, after_state, boundary, ...).",
    "interrogate": "Pressure-test a claim: honesty conditions, hard questions, contradictions.",
    "confirm": "Confirm a claim or honesty condition (user-only — no fabricated rigor).",
    "reject": "Reject a claim or honesty condition.",
    "park": "Move uncertainty into first-class open vagueness instead of forcing an answer.",
    "converge": "Check whether the frame is solid enough to export a spec.",
    "export": "Write the buildable spec — only once the frame converges.",
    "show": "Render the Announcement Frame.",
    "list": "List frames.",
}

_TEXT = (
    "devague turns a vague idea into a buildable spec by working backwards.\n"
    "Start from the announcement, then build an Announcement Frame by capturing\n"
    "claims, interrogating them, parking what's still vague, and converging.\n"
    "The arc — rough capture -> pressure-test -> convergence -> spec — emerges\n"
    "from the moves; it is not a fixed wizard. You (the agent) choose the next\n"
    "move; devague tracks state. LLM-proposed claims and honesty conditions stay\n"
    "'proposed' until the user confirms them.\n\nMoves:\n"
    + "\n".join(f"  {name:<11} {desc}" for name, desc in MOVES.items())
)


def cmd_learn(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        emit_result(
            {"tool": "devague", "version": __version__, "moves": list(MOVES), "summary": _TEXT},
            json_mode=True,
        )
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="Teach devague's working-backwards method.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
