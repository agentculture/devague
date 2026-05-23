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

FIRST_QUESTION = "What's the announcement?"
SUPPORTING_PROMPT = (
    "Pretend this shipped successfully. What would you announce to users, "
    "teammates, or yourself?"
)

# The canonical guided sequence (devague#4). The engine is move-driven, not a
# rigid wizard — this is the recommended arc, with the move that advances each.
STAGES = [
    ("Announcement", "what are we saying shipped?", "new"),
    ("Audience", "who needs this?", "capture --kind audience"),
    ("After", "what changed for them?", "capture --kind after_state"),
    ("Matter", "why is it worth doing?", "capture --kind why_it_matters"),
    ("Before", "what pain made this necessary?", "capture --kind before_state"),
    ("Honest", "what must be true for the announcement to be honest?", "interrogate --honesty"),
    ("FAQ", "what hard questions remain?", "interrogate --hard-question"),
    ("Boundaries", "what are we not promising?", "capture --kind boundary"),
    ("Success", "how will we know?", "capture --kind success_signal"),
    ("Spec", "what should be built?", "converge -> export"),
]

_TEXT = (
    "devague turns a vague idea into a buildable spec by working backwards.\n\n"
    f"First question: {FIRST_QUESTION}\n"
    f"  {SUPPORTING_PROMPT}\n\n"
    "Start from that announcement, then build an Announcement Frame by capturing\n"
    "claims, interrogating them, parking what's still vague, and converging.\n"
    "The arc emerges from the moves; it is not a fixed wizard. You (the agent)\n"
    "choose the next move; devague tracks state. LLM-proposed claims and honesty\n"
    "conditions stay 'proposed' until the user confirms them.\n\n"
    "Guided stages (the recommended sequence — drive them with the moves):\n"
    + "\n".join(
        f"  {i:>2}. {name:<13} {prompt}  [{move}]"
        for i, (name, prompt, move) in enumerate(STAGES, 1)
    )
    + "\n\nMoves:\n"
    + "\n".join(f"  {name:<11} {desc}" for name, desc in MOVES.items())
)


def cmd_learn(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        emit_result(
            {
                "tool": "devague",
                "version": __version__,
                "first_question": FIRST_QUESTION,
                "supporting_prompt": SUPPORTING_PROMPT,
                "stages": [
                    {"step": i, "name": name, "prompt": prompt, "move": move}
                    for i, (name, prompt, move) in enumerate(STAGES, 1)
                ],
                "moves": list(MOVES),
                "summary": _TEXT,
            },
            json_mode=True,
        )
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="Teach devague's working-backwards method.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
